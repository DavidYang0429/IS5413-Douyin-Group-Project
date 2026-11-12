"""Real PostgreSQL login, transaction and concurrency acceptance tests."""
import concurrent.futures
import json
from pathlib import Path
import threading
import time
import unittest
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app
import psycopg
from psycopg.types.json import Jsonb


def connection(actor=1):
    credentials=app.CONFIG['users'][str(actor)]
    return app.connect(credentials['user'], credentials['password'])


def call(conn, action, **payload):
    return conn.execute('SELECT douyin.app(%s,%s)', (action, Jsonb(payload))).fetchone()[0]


class BusinessTests(unittest.TestCase):
    def setUp(self): self.conn=connection()
    def tearDown(self): self.conn.rollback(); self.conn.close()
    def denied(self, action, state, **payload):
        with self.assertRaises(psycopg.Error) as caught:
            with self.conn.transaction(): call(self.conn,action,**payload)
        self.assertEqual(caught.exception.sqlstate,state)
    def publish(self, caption='Acceptance test video'):
        return call(self.conn,'publish',caption=caption,media_url='/media/demo.webm',duration_seconds=3)['video_id']
    def test_identity_cannot_be_supplied(self):
        self.denied('profile','42501',actor_id=2)
    def test_own_profile(self): self.assertEqual(call(self.conn,'profile')['user_id'],1)
    def test_raw_table_access_denied(self):
        with self.assertRaises(psycopg.errors.InsufficientPrivilege): self.conn.execute('SELECT * FROM douyin."USER"')
    def test_cannot_become_admin(self):
        with self.assertRaises(psycopg.errors.InsufficientPrivilege): self.conn.execute('SET ROLE postgres')
    def test_cross_video_reply_rejected(self):
        self.denied('comment','23514',video_id=1,parent_comment_id=6,body_text='Must be rejected')
    def test_missing_parent_rejected(self):
        self.denied('comment','23503',video_id=1,parent_comment_id=999999,body_text='Must be rejected')
    def test_hidden_video_like_rejected(self): self.denied('like','23514',video_id=4)
    def test_hidden_video_comment_rejected(self): self.denied('comment','23514',video_id=4,body_text='Must be rejected')
    def test_hidden_video_collection_rejected(self): self.denied('collect','23514',collection_id=1,video_id=4)
    def test_other_collection_rejected(self): self.denied('collect','42501',collection_id=3,video_id=1)
    def test_other_video_edit_rejected(self): self.denied('edit','42501',video_id=2,caption='Cannot edit another author')
    def test_other_video_hide_rejected(self): self.denied('hide','42501',video_id=2)
    def test_other_video_topic_rejected(self): self.denied('tag','42501',video_id=2,topic_id=1)
    def test_self_follow_rejected(self): self.denied('follow','23514',target_user_id=1)
    def test_injection_remains_text(self):
        caption="'; DROP TABLE douyin.\"VIDEO\"; --"
        vid=self.publish(caption)
        self.assertTrue(any(v['video_id']==vid and v['caption']==caption for v in call(self.conn,'feed')))
    def test_publish_comment_collect_and_hide(self):
        vid=self.publish()
        comment=call(self.conn,'comment',video_id=vid,body_text='First comment')['comment_id']
        call(self.conn,'comment',video_id=vid,parent_comment_id=comment,body_text='A reply')
        call(self.conn,'like',video_id=vid)
        cid=call(self.conn,'create_collection',name='Acceptance temporary collection')['collection_id']
        first=call(self.conn,'collect',video_id=vid,collection_id=cid)
        second=call(self.conn,'collect',video_id=vid,collection_id=cid)
        self.assertEqual(first['item_no'],second['item_no']); self.assertTrue(second['already_present'])
        call(self.conn,'hide',video_id=vid)
        self.denied('comment','23514',video_id=vid,body_text='Cannot add after hiding')
        call(self.conn,'unhide',video_id=vid)
        self.assertEqual(len(call(self.conn,'comments',video_id=vid)),2)
    def test_operator_report_executes(self):
        self.assertGreaterEqual(len(self.conn.execute("SELECT douyin.report('Q03')").fetchone()[0]),7)
    def test_non_operator_report_denied(self):
        with connection(2) as c:
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):c.execute("SELECT douyin.report('Q01')")
    def test_login_role_is_real_identity(self):
        with connection(2) as c:self.assertEqual(call(c,'profile')['user_id'],2)


class ConcurrentTests(unittest.TestCase):
    def fixtures(self):
        with connection() as c:
            videos=[call(c,'publish',caption='Concurrency verification '+str(i),media_url='/media/demo.webm',duration_seconds=3)['video_id'] for i in range(2)]
            cid=call(c,'create_collection',name='Concurrency verification '+str(time.time_ns()))['collection_id']
        return videos,cid
    def test_two_collectors_allocate_distinct_numbers(self):
        videos,cid=self.fixtures(); start=threading.Barrier(2)
        def add(vid):
            with connection() as c:
                start.wait(timeout=5)
                return call(c,'collect',video_id=vid,collection_id=cid)['item_no']
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(add,videos,timeout=20))
        self.assertEqual(sorted(results),[1,2])
    def test_hiding_waits_for_prior_interaction(self):
        videos,_=self.fixtures();vid=videos[0]
        a=connection();call(a,'comment',video_id=vid,body_text='Committed before hiding')
        started=threading.Event()
        def hide():
            with connection() as b:
                started.set();call(b,'hide',video_id=vid)
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future=pool.submit(hide);self.assertTrue(started.wait(5));time.sleep(.4)
            self.assertFalse(future.done(),'Hide must wait for interaction FOR SHARE lock')
            a.commit();a.close();future.result(timeout=15)
        with connection(2) as c:
            with self.assertRaises(psycopg.errors.CheckViolation):call(c,'like',video_id=vid)


if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    target=Path(__file__).resolve().parents[2]/'验证记录/04_business_tests.json'
    target.write_text(json.dumps({'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'passed':result.wasSuccessful(),'scope':'Actual PostgreSQL login roles, transaction rollback probes and two-session concurrency. Concurrency fixtures retained; no historical data deleted.'},indent=2)+'\n')
    sys.exit(not result.wasSuccessful())
