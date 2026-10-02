"""Public staging smoke: private credentials read only in memory; no cookie artifacts."""
import argparse
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--url', default='https://airoom.nolimlabs.uk')
parser.add_argument('--expected-build', required=True, help='Exact deployed source commit')
parser.add_argument('--credentials', type=Path, default=Path('instance/reviewer-credentials.txt'))
args = parser.parse_args()
base = args.url.rstrip('/')
if not base.startswith('https://'):
    parser.error('Public smoke requires HTTPS')
out = Path(os.environ.get('CLUB_EVIDENCE_DIR', 'instance/public-evidence'))
out.mkdir(parents=True, exist_ok=True)
password = args.credentials.read_text().split('Password: ', 1)[1].splitlines()[0]
result={'url':base,'pages':[],'errors':[]}
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
    context=browser.new_context(viewport={'width':1440,'height':900},reduced_motion='reduce')
    page=context.new_page()
    page.on('pageerror',lambda error:result['errors'].append(str(error)))
    health_response=context.request.get(base+'/health')
    assert health_response.status == 200
    result['health']=health_response.json()
    assert result['health']['status'] == 'ok'
    assert result['health']['build'] == args.expected_build, 'Public build differs from candidate'
    assert result['health']['schema'] == 6
    for route in ['/#/orbit/home','/#/campus/home']:
        page.goto(base+route)
        page.wait_for_url('**/prototypes/**')
        page.locator('#app').wait_for()
        assert len(page.locator('#app').inner_text())>100
        page.screenshot(path=str(out/('prototype-'+route.split('/')[2]+'.png')))
        result['pages'].append({'route':route,'resolved':page.url,'rendered':True})
    page.goto(base+'/login')
    page.get_by_label('Почта',exact=True).fill('member@example.test')
    page.get_by_label('Пароль',exact=True).fill(password)
    page.get_by_role('button',name='Войти',exact=True).click()
    page.wait_for_url(base+'/')
    cookies=[c for c in context.cookies() if c['name']=='session']
    result['secure_session']=bool(cookies) and all(c['secure'] and c['httpOnly'] and c['sameSite']=='Lax' for c in cookies)
    assert result['secure_session']
    for route in ['/','/routes/path-essentials','/profile','/lessons/foundations-start-01']:
        response=page.goto(base+route)
        assert response.status==200
        assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
        result['pages'].append({'route':route,'status':response.status})
    video=page.locator('video')
    video.evaluate('(v)=>v.play()')
    page.wait_for_function('() => document.querySelector("video").currentTime>1')
    result['public_video_playback']=True
    page.screenshot(path=str(out/'public-lesson.png'))
    page.set_viewport_size({'width':390,'height':844})
    page.goto(base+'/routes/path-essentials')
    assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
    page.screenshot(path=str(out/'public-route-mobile.png'),full_page=True)
    assert context.request.get(base+'/admin').status==403
    assert context.request.get(base+'/admin/measurement').status==403
    result['learner_admin_denied']=True
    browser.close()
assert not result['errors']
(out/'public.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps(result,ensure_ascii=False))
