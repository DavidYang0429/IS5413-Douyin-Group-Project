"""Build the final Word report using verified artifacts, not invented outcomes."""
from pathlib import Path
import json,re,textwrap
from docx import Document
from docx.shared import Inches,Pt,RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT

BASE=Path(__file__).resolve().parents[1]
OUT=BASE/'交付物';OUT.mkdir(exist_ok=True)
queries=json.loads((BASE/'验证记录/06_final_queries.json').read_text())
evidence=json.loads((BASE/'验证记录/05_final_runtime.json').read_text())
business=json.loads((BASE/'验证记录/04_business_tests.json').read_text())
browser=json.loads((BASE/'验证记录/browser/browser_results.json').read_text())
assert business['passed'] and browser['passed']
assert all(t['passed'] for t in evidence['structural_tests']+evidence['immutability_tests'])
d=Document();sec=d.sections[0];sec.page_width=Inches(8.27);sec.page_height=Inches(11.69)
sec.top_margin=sec.bottom_margin=Inches(.6);sec.left_margin=sec.right_margin=Inches(.7)
for s in d.styles:
 if s.type==1:
  s.font.name='Arial';s.font.color.rgb=RGBColor(0,0,0)
  if s.element.pPr is not None:
   for child in list(s.element.pPr):
    if child.tag==qn('w:pBdr'):s.element.pPr.remove(child)
n=d.styles['Normal'];n.font.size=Pt(10.3);n.paragraph_format.space_after=Pt(5);n.paragraph_format.line_spacing=1.06
for name,size in [('Title',25),('Subtitle',12),('Heading 1',15),('Heading 2',11.2)]:
 s=d.styles[name];s.font.size=Pt(size);s.paragraph_format.space_before=Pt(8);s.paragraph_format.space_after=Pt(5)
d.core_properties.title='Database Design and Implementation for a Short Video Platform'
d.core_properties.author='Save 50 pounds'
f=sec.footer.paragraphs[0];f.alignment=WD_ALIGN_PARAGRAPH.RIGHT
f.add_run('IS5413   Save 50 pounds   |   ')
for instr in ['PAGE','NUMPAGES']:
 if instr=='NUMPAGES':f.add_run(' / ')
 fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),instr);f._p.append(fld)
for run in f.runs:run.font.size=Pt(8)
md=[]
def p(text,style=None):d.add_paragraph(text,style);md.append(text+'\n')
def h(text):d.add_heading(text,1);md.append('## '+text+'\n')
def h2(text):d.add_heading(text,2);md.append('### '+text+'\n')
def page():d.add_page_break();md.append('\n---\n')
def table(headers,rows,widths=None,size=9):
 t=d.add_table(rows=1,cols=len(headers));t.autofit=False
 if widths:
  for c,w in zip(t.columns,widths):c.width=Inches(w)
 for c,text in zip(t.rows[0].cells,headers):c.text=str(text)
 for values in rows:
  for c,text in zip(t.add_row().cells,values):c.text='NULL' if text is None else str(text)
 for i,row in enumerate(t.rows):
  for j,c in enumerate(row.cells):
   if widths:c.width=Inches(widths[j])
   c.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
   pr=c._tc.get_or_add_tcPr();b=OxmlElement('w:tcBorders')
   for side in ['top','left','bottom','right']:
    el=OxmlElement('w:'+side);el.set(qn('w:val'),'single');el.set(qn('w:sz'),'4');el.set(qn('w:color'),'D9D9D9');b.append(el)
   pr.append(b)
   sh=OxmlElement('w:shd');sh.set(qn('w:fill'),'E7EDF1' if i==0 else 'FFFFFF');pr.append(sh)
   for para in c.paragraphs:
    para.paragraph_format.space_before=Pt(2);para.paragraph_format.space_after=Pt(2);para.paragraph_format.line_spacing=1.02
    for r in para.runs:r.font.size=Pt(size);r.bold=(i==0)
  trpr=row._tr.get_or_add_trPr();nosplit=OxmlElement('w:cantSplit');trpr.append(nosplit)
  if i==0:trpr.append(OxmlElement('w:tblHeader'))
 d.add_paragraph().paragraph_format.space_after=Pt(2)
 md.append('| '+' | '.join(headers)+' |\n| '+' | '.join('---' for _ in headers)+' |\n'+'\n'.join('| '+' | '.join('NULL' if v is None else str(v).replace('\n',' ') for v in row)+' |' for row in rows)+'\n')
def code(sql):
 sql=re.sub(r'^--[^\n]*\n?','',sql,flags=re.M).strip()
 for line in sql.splitlines():
  pieces=textwrap.wrap(line,width=110,break_long_words=False,break_on_hyphens=False,replace_whitespace=False) or ['']
  for piece in pieces:
   para=d.add_paragraph();para.paragraph_format.space_after=Pt(0);para.paragraph_format.line_spacing=Pt(10)
   r=para.add_run(piece);r.font.name='Courier New';r.font.size=Pt(8.3)
 d.paragraphs[-1].paragraph_format.space_after=Pt(4)
 md.append('```sql\n'+sql+'\n```\n')
def picture(path,width):
 para=d.add_paragraph();para.alignment=WD_ALIGN_PARAGRAPH.CENTER;para.add_run().add_picture(str(path),width=Inches(width))
 md.append('![]('+str(path.relative_to(BASE))+')\n')

p('Database Design and Implementation for a Short Video Platform','Title')
p('IS5413 Database Management\nFinal Project Report 2026/27 A','Subtitle')
p('Team name  Save 50 pounds')
p('Public repository edition. Team member names and student IDs are retained only in the private course submission.')
h('1 Project outcome and scope')
p('We implemented Loop, a simplified Douyin-inspired database application. The system supports video publication, optional music, topic tagging, comments and replies, likes, directed follows and personal collections. A local browser interface connects to a Python service and an actual Supabase-hosted PostgreSQL 17.11 database. The application is an independent course design, not a reconstruction of Douyin\'s internal schema.')
p('The final model contains exactly 10 entity types and 10 business relations with 43 attributes. It includes associative entities, a weak collection item and a recursive comment relationship. The logical schema is in 3NF under its declared dependencies. Physical implementation adds keys, checks, indexes, guarded database functions and triggers without adding business entities.')
p(f'We initially loaded 69 synthetic records. Real acceptance tests and browser demonstrations added retained test records; the final catalog snapshot contains {sum(evidence["catalog"]["row_counts"].values())} rows. Thirty-one structural checks, 21 authenticated business and concurrency tests, four immutability probes and 14 browser acceptance checks passed. The ten required query tasks were executed against the live database; selected returned columns are presented in Sections 9 to 13.')
h2('Scope boundary')
p('Recommendation algorithms, watch history, live streaming, commerce, messaging, advertising, payments, transcoding and copyright management are excluded. An original generated WebM demonstrates playback. Media files remain outside relational tables, and synthetic example.invalid seed URLs do not represent accessible third-party content.')
p('Report evidence was captured on 12 November 2026. Database creation, implementation and verification are complete for this prototype; this document does not claim a production deployment, a load test or a completed classroom presentation.')

page();h('2 Conceptual design for content')
p('A user may be both viewer and creator. Each video has one creator and zero or one music record. Video-topic pairs are unique. Every comment has one author and one video; replies point to an existing comment on the same video.')
picture(OUT/'ER1.png',6.65)
p('Figure 1 Content and comments. Endpoint labels give the number of adjacent entity instances for one opposite instance. VIDEO_TOPIC explicitly resolves the M:N video-topic relationship and counts as one of the ten entities. COMMENT has an independent primary identifier; its optional recursive parent does not create another entity type.')
p('The parent must already exist, self-parenting is rejected and ancestry is immutable after insertion. Starting from the acyclic seed data, these conditions preserve an acyclic reply graph. The system stores video_id on every comment so video retrieval does not require walking to a root comment.')

page();h('3 Conceptual design for social interactions')
picture(OUT/'ER2.png',6.65)
p('Figure 2 Social and collection view. Repeated USER boxes indicate follower and followed roles of the same entity. A directed follow pair is unique and self-following is forbidden. Likes represent the current user-video association; unlike and re-like create a new association time.')
p('COLLECTION_ITEM is a weak entity identified by its collection and item_no partial key. Each collection has one owner. Collection names are unique within an owner, and each video occurs at most once within a collection. The same video may be in several collections. Item numbers are stable identifiers, not a continuously renumbered display order.')
p('The combined inventory is USER, VIDEO, MUSIC, TOPIC, COMMENT, VIDEO_TOPIC, VIDEO_LIKE, FOLLOW, COLLECTION and COLLECTION_ITEM. Weak and associative entities are included in the count of ten. Empty accounts and collections are valid. Hiding a video retains its historical interactions but prevents new ones.')

schema=(BASE/'sql/postgresql/01_schema.sql').read_text()
blocks=re.findall(r'CREATE TABLE douyin\."(\w+)" \((.*?)\n\);',schema,re.S)
relations={};fieldrows=[]
for name,body in blocks:
 fields=[]
 for line in body.splitlines():
  m=re.match(r'    (\w+) (BIGINT|INTEGER|VARCHAR\(\d+\)|DECIMAL\(\d+,\d+\)|TIMESTAMPTZ\(3\)|TEXT)(.*)',line)
  if not m:continue
  field,typ,tail=m.groups();fields.append(field)
  rules=[]
  if 'GENERATED' in tail:rules.append('Identity PK; > 0')
  elif field in ('user_id','video_id','topic_id','follower_id','followed_id','collection_id','item_no'):
   if re.search(r'PRIMARY KEY \([^)]*\b'+field+r'\b',body):rules.append('Composite PK')
  if 'NOT NULL' in tail:rules.append('NOT NULL')
  else:rules.append('Nullable')
  fk=re.search(r'FOREIGN KEY \('+field+r'\) REFERENCES douyin\."(\w+)" \((\w+)\)',body)
  if fk:rules.append('FK '+fk[1]+'.'+fk[2])
  if 'DEFAULT' in tail and 'GENERATED' not in tail:rules.append('Default '+tail.split('DEFAULT ',1)[1].rstrip(','))
  fieldrows.append((name+'.'+field,typ,'; '.join(rules)))
 pk=re.search(r'PRIMARY KEY \(([^)]+)\)',body)[1]
 aks=re.findall(r'UNIQUE \(([^)]+)\)',body)
 fks=re.findall(r'FOREIGN KEY \((\w+)\) REFERENCES douyin\."(\w+)" \((\w+)\)',body)
 relations[name]=(fields,pk,aks,fks)
page();h('4 Relational schema and mapping')
p('PK denotes the selected primary key and AK another candidate key. All attributes are NOT NULL except VIDEO.music_id and COMMENT.parent_comment_id. Names use quoted uppercase table identifiers in the private douyin schema.')
for name,(fields,pk,aks,fks) in relations.items():
 h2(name)
 para=d.add_paragraph('('+', '.join(fields)+')');para.paragraph_format.space_after=Pt(2)
 for r in para.runs:r.font.size=Pt(9.2)
 text='PK('+pk+')'+''.join('; AK('+a+')' for a in aks)
 if fks:text+='; '+ '; '.join(f'{a} → {b}.{c}' for a,b,c in fks)
 para=d.add_paragraph(text);para.paragraph_format.space_after=Pt(3)
 for r in para.runs:r.font.size=Pt(8.8)
 md.append(name+'('+', '.join(fields)+')\n'+text+'\n')
p('Strong entities map to their own relations; associations use composite participant keys. The weak item includes its owner identifier and a partial key. Recursive parent_comment_id is a nullable self-FK. Ownership is obtained through COLLECTION rather than duplicated in items.')

page();h('5 Functional dependencies and normalization')
p('N denotes all attributes outside the selected primary key, including alternate-key attributes when present. These FD generators express the declared business rules; names, media URLs and timestamps are not assumed unique unless explicitly specified.')
fds=[('USER','user_id → N; phone → user_id','user_id; phone'),('VIDEO','video_id → N','video_id'),('MUSIC','music_id → N','music_id'),('TOPIC','topic_id → topic_name; topic_name → topic_id','topic_id; topic_name'),('COMMENT','comment_id → N','comment_id'),('VIDEO_TOPIC','(video_id, topic_id) → tagged_at','(video_id, topic_id)'),('VIDEO_LIKE','(user_id, video_id) → liked_at','(user_id, video_id)'),('FOLLOW','(follower_id, followed_id) → followed_at','(follower_id, followed_id)'),('COLLECTION','collection_id → N; (owner_id, collection_name) → collection_id','collection_id; (owner_id, collection_name)'),('COLLECTION_ITEM','(collection_id, item_no) → N; (collection_id, video_id) → item_no','(collection_id, item_no); (collection_id, video_id)')]
table(['Relation','FD generators','Candidate keys'],[(n.replace('COLLECTION_ITEM','COLLECTION_\nITEM'),fd,k) for n,fd,k in fds],[1.25,3.25,2.3],8.7)
p('1NF. Each attribute contains a single value. Multiple topics, follows, likes, comments and collection entries occupy separate rows. artist_name is one display-credit string; a structured multi-artist catalogue is outside scope.')
p('2NF. Every non-prime attribute depends on each complete candidate key. liked_at depends on the user-video pair, not the user or video alone. Neither item_no nor video_id alone identifies a collection entry; added_at depends on the whole of either candidate key.')
p('3NF. For each non-trivial FD X → a, X is a superkey or a is prime. Every generator above has a candidate key as determinant and no additional non-key determinant is assumed. Thus these relations satisfy BCNF and therefore 3NF under this dependency set. Cross-row permissions, visibility and parent consistency are integrity rules, not extra intra-relation FDs.')
p('A flattened video record containing creator_phone would have video_id → creator_id → creator_phone. Because a creator can publish many videos, creator_id is not a key of that flattened relation. Splitting creator details into USER is lossless because the shared creator identifier determines the USER fragment; both dependencies are preserved locally. Music and topic metadata are separated for the same update-consistency reason.')
p('No denormalization was applied. Like counts, follower counts, topic popularity and publication counts are computed from detail rows; the small prototype does not justify stored aggregate counters or their maintenance complexity.')

page();h('6 Physical design for accounts and content')
p('Implementation uses PostgreSQL 17.11, not the initially considered MySQL dialect. Six single-column keys use generated identities. Positive-ID CHECKs compensate for the absence of UNSIGNED; signed BIGINT and INTEGER limits are documented in the data dictionary.')
p('TIMESTAMPTZ(3) stores millisecond-resolution time points; fixtures are UTC and display follows the connection time zone. phone, topic/collection names and status values use deterministic C collation. Case-distinct names are allowed. The application applies NFC normalization and strips surrounding whitespace before user text is written.')
table(['Attribute','PostgreSQL type','Physical rule'],fieldrows[:19],[2.0,1.4,3.4],8.7)
p('Additional domain checks enforce ASCII, nonempty trimmed phone values, positive duration_seconds, nonempty topic names and allowed statuses. Captions may be empty. Media/audio URLs are external locations; the relational database does not store media bytes or validate remote availability.')

page();h('7 Physical design for interactions and collections')
table(['Attribute','PostgreSQL type','Physical rule'],fieldrows[19:],[2.0,1.4,3.4],8.4)
p('Four alternate unique keys enforce phone, topic name, collection name per owner and video occurrence per collection. Other pair uniqueness follows composite PKs. Foreign keys are non-deferrable with default NO ACTION; no cascading deletion is configured. New interactions on hidden content are rejected by triggers, while existing rows remain referenced.')
p('The database contains 10 PKs, 4 alternate UNIQUE constraints, 14 FKs and 16 CHECKs. Six of the CHECKs enforce positive identity values. TRIM checks target ordinary spaces; application normalization does not replace database ownership checks.')

page();h('8 Transaction and authorization implementation')
p('The browser connects only to a local Python HTTP service bound to 127.0.0.1. Login is checked by PostgreSQL using one of five provisioned LOGIN roles. The service maintains an expiring HttpOnly SameSite session and a CSRF token; each database call uses the authenticated role, TLS CA verification and hostname verification. Passwords are held in local private configuration and server memory, never in frontend source or the submitted archive.')
p('Application data stay in a private douyin schema. Demo roles receive USAGE and EXECUTE on a small application function, not direct table access, schema creation, role creation or administrator membership. The privileged function fixes search_path, qualifies business tables and derives the actor from SESSION_USER. It checks the role format and ACTIVE account before dispatching a fixed action whitelist. Supplied actor_id, creator_id, owner_id or author_id fields are rejected.')
code("""-- Trusted login identity, not a caller-controlled payload
actor := substring(session_user from '([1-5])$')::bigint;
SELECT owner_id INTO owner
FROM douyin.\"COLLECTION\"
WHERE collection_id = cid FOR UPDATE;
IF owner IS DISTINCT FROM actor THEN
  RAISE EXCEPTION 'Only the owner may modify this collection'
    USING ERRCODE = '42501';
END IF;
SELECT coalesce(max(item_no), 0) + 1 INTO n
FROM douyin.\"COLLECTION_ITEM\" WHERE collection_id = cid;""")
p('Collection insertion locks the parent collection before choosing the next local number. Concurrent requests for different videos serialize and obtain distinct numbers. The unique video-per-collection key handles repeated saves, which return the existing number. Deleting an item does not renumber the remaining items; trailing numbers can be reused.')
code("""SELECT visibility_status INTO state
FROM douyin.\"VIDEO\" WHERE video_id = NEW.video_id FOR SHARE;
IF state <> 'PUBLISHED' THEN
  RAISE EXCEPTION 'Hidden videos cannot receive new interactions'
    USING ERRCODE = '23514';
END IF;""")
p('Like, comment and collection-item triggers hold FOR SHARE on the target video. Hiding updates that same video and requires a conflicting row lock: a completed interaction may precede hiding, but later new interactions fail. Comment triggers require an existing parent on the same video and reject self-parenting. Comment identity, author, video and parent, plus video creator and collection owner, are immutable. Only checked creator/owner operations are exposed.')
p('RLS remains default-deny for direct/API table access. SECURITY DEFINER is a deliberate narrow function gateway, not a claim that RLS policies implement ownership. The operator role alone may execute the ten fixed report queries; arbitrary SQL is never accepted by the HTTP interface. Database owners and provisioners remain trusted administrators.')

columns={
'Q01':['video_id','caption','music_title'],'Q02':['topic_name','video_id','caption'],
'Q03':['video_id','like_count'],'Q04':['comment_id','parent_comment_id','depth','display_text'],
'Q05':['direction','user_id','nickname'],'Q06':['user_id','nickname'],
'Q07':['collection_id','item_no','video_id'],'Q08':['video_id','like_count','popularity_rank'],
'Q09':['user_id','published_video_count'],'Q10':['topic_name','published_video_count']}
for pair in range(5):
 page();h(f'{9+pair} SQL tasks {pair*2+1} and {pair*2+2}')
 p('Actual live execution results captured '+queries['captured_at_utc']+'. Selected output columns and at most six rows are shown; full SQL and returned rows are included in 06_final_queries.json. Synthetic demonstration writes explain differences from the original 69-row fixture.')
 for q in queries['queries'][pair*2:pair*2+2]:
  title={'Q01':'Creator videos','Q02':'Topic search','Q03':'Per video like counts','Q04':'Comment tree','Q05':'Followers and following','Q06':'Mutual follows','Q07':'Collection contents','Q08':'Video popularity ranks','Q09':'Active creator publication counts','Q10':'Topic popularity'}[q['id']]
  h2(q['id']+' '+title)
  code(q['sql'])
  p('Result '+str(len(q['rows']))+' rows')
  keys=columns[q['id']];r=q['rows'][:6]
  widths=([1.0,1.0,.55,4.25] if q['id']=='Q04' else None)
  table(['parent_id' if k=='parent_comment_id' else k for k in keys],[[row[k] for k in keys] for row in r],widths,8.4)

page();h('14 Verification and regression evidence')
table(['Layer','Executed acceptance','Result'],[
('Structure','Duplicate keys, bad FKs, invalid domains and valid alternatives','31 passed'),
('Database identities','Real role login, denied actor substitution and denied SET ROLE postgres','Passed'),
('Ownership','Foreign video edit/hide/topic update and foreign collection insert','Rejected'),
('Visibility and replies','Hidden-video writes; cross-video and missing-parent replies','Rejected'),
('Immutable identities','Self-parenting; reparenting; video creator and collection owner changes','4 passed'),
('Workflow','Publish, comment, reply, like, collect, hide and restore in a rollback transaction','Passed'),
('Concurrency','Two collectors obtain numbers 1 and 2; hiding waits for prior interaction','2 passed'),
('Browser and HTTP','Login, publish, comment, like, collection, reports, CSRF and ownership','14 passed'),
('Responsive display','390px viewport; no horizontal document overflow','Passed'),
],[1.15,4.5,1.15],9)
p('The authenticated business suite contains 21 tests in total, including the two concurrency scenarios. The initial structural suite has 25 rejected invalid writes and six accepted alternatives. Successful structural probes are rolled back by exception subtransactions. General business probes roll back; dedicated concurrency and browser fixtures remain retained for audit, with concurrency videos hidden after verification. No historical seed records were deleted.')
p('The concurrency test uses separate real database connections. One transaction inserts an interaction while holding its video lock; a second hides the video and remains pending until the first commits. A subsequent interaction fails. Another test starts two collection inserts together and verifies the assigned local numbers are 1 and 2.')
p('An initial test run exposed a shared-trigger record-field error: PostgreSQL resolved a comment-only NEW field for likes and collection items. The fix moved that field reference inside a COMMENT-specific branch and was applied as guard_record_field_resolution. The complete business suite then passed. Browser tests also exposed and fixed a mobile grid overflow; the final 390px check passed.')
p('Evidence files retain the original failure summary and the passing rerun. The final structural and immutability results are in 05_final_runtime.json, business results in 04_business_tests.json, and screenshots plus browser_results.json in the browser evidence folder. Assertions on saved historical evidence are distinguished from new database executions.')

page();h('15 Working prototype')
p('The desktop interface supports the tested workflow and displays actual server results. The original bundled animation is used as a consistent playable placeholder for synthetic video records; it is not represented as authentic Douyin media.')
picture(BASE/'验证记录/browser/02_feed.png',5.7)
p('Figure 3 Real browser feed during acceptance testing. New test records remain visible to their owner; no static mock response is used.')
picture(BASE/'验证记录/browser/05_report.png',5.7)
p('Figure 4 The report screen executes a fixed live SELECT whitelist, including zero-like rows. This capture precedes hiding the dedicated concurrency fixtures; the query tables use a later final live snapshot.')

page();h('16 Index evaluation and delivery')
p('There are 23 explicit indexes: 10 primary, four alternate unique and nine ordinary indexes. PostgreSQL does not automatically index referencing FK columns, so the physical design explicitly includes the relevant leading columns.')
table(['Index family','Reason'],[
('VIDEO(creator_id, visibility_status, published_at)','Creator lists and creator FK lookups'),
('VIDEO(music_id); COMMENT(author_id), COMMENT(parent_comment_id)','Music/author FKs and direct reply retrieval'),
('COMMENT(video_id, comment_status, created_at)','Visible comments for a video'),
('VIDEO_TOPIC(topic_id, video_id)','Reverse topic lookup'),
('VIDEO_LIKE(video_id, user_id)','Like counts by video'),
('FOLLOW(followed_id, follower_id)','Incoming follower lookup'),
('COLLECTION_ITEM(video_id, collection_id)','Reverse video reference lookup'),
],[3.6,3.2],8.7)
plan=evidence['explain'][0]
p(f'One EXPLAIN ANALYZE BUFFERS observation of the like-count query reported {plan["Execution Time"]} ms execution time and {plan["Plan"]["Actual Rows"]} output rows on the small demonstration dataset at that capture. The plan used the video and reverse-like indexes. This is a warm, tiny-data observation, not a comparison proving speedup or a throughput benchmark. No denormalization was justified.')
p('The project security advisor reported informational RLS-without-policy notices, consistent with the intentional function-only gateway. No browser/API table grants were added. Index-use notices on the initial small workload were reviewed without deleting candidate FK indexes merely to silence diagnostics.')
h2('Reproduction and limitations')
p('The submitted source contains PostgreSQL initialization, fixed synthetic data, business routines, the report whitelist, verification SQL, a local Python prototype, pinned driver requirements, the public TLS CA, an original demo clip, tests and run instructions. setup_demo.py provisions a fresh empty Supabase project and refuses an existing business schema or role set. Private passwords, local virtual environments and session state are excluded from the submission archive.')
p('The prototype requires a reachable Supabase project; free projects may pause after inactivity, so the team must check connectivity before the five-minute demonstration. It supports five controlled demo roles rather than open registration or account recovery. It is a course prototype, not a production deployment or a tested public service. The group leader remains responsible for uploading one team submission.')
h2('References')
for text in [
'IS5413 Project Assignment 2026/27 A, Steps 1 to 4; instructor supplementary limit of ten ER entities.',
'PostgreSQL 17 documentation, CREATE POLICY and Session Information Functions: https://www.postgresql.org/docs/17/sql-createpolicy.html and https://www.postgresql.org/docs/17/functions-info.html',
'Supabase documentation, database connections and SSL: https://supabase.com/docs/guides/database/connecting-to-postgres and https://supabase.com/docs/guides/platform/ssl-enforcement',
'Psycopg documentation, installation and transactions: https://www.psycopg.org/psycopg3/docs/basic/install.html',
]:p(text)
path=OUT/'IS5413_Final_Report_Douyin.docx';d.save(path)
(BASE/'Final_Report_Douyin.md').write_text('# Database Design and Implementation for a Short Video Platform\n\n'+'\n'.join(md))
print(path)
