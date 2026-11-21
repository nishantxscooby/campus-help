import {expect, test} from '@playwright/test';

const appeal = 'What is the deadline to file an appeal?';
const field = page=>page.getByRole('textbox',{name:'Message Campus Help'});
const authority = 'Who is authorized to archive Form Z under the records policy?';
async function ask(page,question) {
  await field(page).fill(question);
  const response=page.waitForResponse(r=>r.url().endsWith('/ask'));
  await field(page).press('Enter');
  return (await response).json();
}

test('suggestion sends appeal to the API and groups page 5 sources',async({page,context})=>{
  await context.grantPermissions(['clipboard-read','clipboard-write']);
  await page.goto('/');
  const response=page.waitForResponse(r=>r.url().endsWith('/ask'));
  await page.getByRole('button',{name:'Appeal deadline'}).click();
  expect((await (await response).json()).excerpts).toHaveLength(2);
  await expect(page.locator('blockquote')).toContainText('5 working days of the service of the order.');
  await expect(page.getByText('Not independently verified · For reference only.')).toBeVisible();
  const link=page.getByRole('link',{name:'Discipline Handbook · Page 5'});
  await expect(link).toHaveCount(1);
  const pdf=page.context().waitForEvent('response',r=>r.url().includes('/documents/handbook/pdf') && r.status()===200);
  await link.click();
  expect((await pdf).headers()['content-type']).toBe('application/pdf');
  await expect(page.getByText('6. Appeal:',{exact:true})).toBeHidden();
  await page.getByText('View source details').click();
  await expect(page.getByText('6. Appeal:',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Copy response'}).click();
  expect(await page.evaluate(()=>navigator.clipboard.readText())).toContain('Not independently verified');
});

for (const [question,term,num] of [
  ['What gets me restigate','Did you mean rustication?',8],
  ['what makes me debar','I found no student debarment rule in the indexed discipline handbook',4],
]) {
  test(question,async({page})=>{
    await page.goto('/');
    await ask(page,question);
    await expect(page.locator('.answer > p').first()).toContainText(term);
    await expect(page.getByRole('link',{name:'Discipline Handbook · Page '+num})).toBeVisible();
    if(num===8) {
      const reply=page.waitForResponse(r=>r.url().endsWith('/ask'));
      await page.getByRole('button',{name:/Ask “Can I be rusticated/}).click();
      expect((await (await reply).json()).status).toBe('insufficient_evidence');
    }
  });
}

test('mobile drawer, search, themes, saved chats and removal',async({page})=>{
  await page.setViewportSize({width:390,height:844});
  await page.goto('/');
  await ask(page,appeal);
  await page.getByRole('button',{name:'Start new conversation'}).click();
  await ask(page,'Which scholarships are available?');
  await expect(page.locator('.answer .chip').first()).toContainText('Scholarship Policy');
  const open=()=>page.getByRole('button',{name:'Open sidebar'}).click();
  await open();
  const drawer=page.getByRole('dialog');
  await drawer.getByLabel('Search conversations').fill('deadline');
  await drawer.getByRole('button',{name:appeal,exact:true}).click();
  await expect(page.locator('.user')).toHaveText(appeal);
  await open();
  await drawer.getByRole('button',{name:'Dark theme'}).click();
  await page.keyboard.press('Escape');
  await page.reload();
  await expect(page.locator('html')).toHaveAttribute('data-theme','dark');
  await expect(page.locator('.user')).toHaveText(appeal);
  await open();
  page.on('dialog',d=>d.accept());
  await drawer.getByRole('button',{name:'Delete '+appeal}).click();
  await drawer.getByRole('button',{name:'Clear history'}).click();
  await expect(page.getByRole('heading',{name:'Campus Help'})).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
});

test('network error and retry of the same turn',async({page})=>{
  await page.goto('/');
  await page.route('**/ask',route=>route.abort(),{times:1});
  await field(page).fill(appeal);
  await field(page).press('Enter');
  await expect(page.getByRole('alert')).toContainText('connection');
  await page.getByRole('button',{name:'Retry',exact:true}).click();
  await expect(page.locator('blockquote')).toContainText('5 working days');
  await expect(page.locator('article')).toHaveCount(1);
});

for (const [name,port,question,expected] of [
  ['approved',8102,authority,'Verified from handbook'],
  ['wrong action',8102,authority.replace('archive','destroy'),'review'],
  ['wrong actor',8102,'Can students archive Form Z under the records policy?','handbook'],
  ['pending',8103,authority,'review'],
  ['rejected',8104,authority,'review'],
  ['incorrect citation',8105,authority,'complete rule'],
  ['changed PDF',8106,authority,'handbook is unavailable'],
  ['missing source',8101,appeal,'handbook is unavailable'],
]) {
  test(name,async({page})=>{
    await page.goto('http://127.0.0.1:'+port+'/');
    const body=await ask(page,question);
    if(name==='approved') {
      await expect(page.locator('.note')).toHaveText(expected);
      await expect(page.locator('.answer')).toContainText('The Records Office may archive Form Z under the records policy.');
      await expect(page.getByRole('link',{name:/Page 1/})).toHaveAttribute('href','/documents/handbook/pdf#page=1');
    } else {
      expect(body.status).not.toBe('answered');
      await expect(page.locator('.note')).toHaveCount(0);
      await expect(page.locator('article')).toContainText(new RegExp(expected,'i'));
    }
  });
}

test('malformed JSON is rejected',async({request})=>{
  expect((await request.post('/ask',{headers:{'Content-Type':'application/json'},data:'{bad'})).status()).toBe(422);
});

test('malformed storage does not block a new conversation',async({page})=>{
  await page.addInitScript(()=>localStorage.setItem('campus-help.chats.v1','{bad'));
  await page.goto('/');
  await expect(page.getByRole('heading',{name:'Campus Help'})).toBeVisible();
  const result=await ask(page,'What happens if I break hostel rules?');
  expect(result.reason).toBe('clarify_hostel');
  await expect(page.locator('.answer')).toContainText('Which hostel rule');
});

test('open topic and contextual penalty follow-up use live authenticated sources', async ({page})=>{
  await page.goto('/');
  const first=await ask(page,'smoking');
  expect(first.excerpts.some(s=>s.pdf_page_number===9 && s.exact_quotation.includes('Cigarettes'))).toBe(true);
  await expect(page.getByRole('link',{name:/Page 9/}).first()).toBeVisible();
  const outgoing=page.waitForRequest(r=>r.url().endsWith('/ask'));
  const next=await ask(page,'And what if it is my second offence?');
  expect((await outgoing).postDataJSON().history).toEqual(['smoking']);
  expect(next.status).toBe('insufficient_evidence');
  expect(next.excerpts.some(s=>s.exact_quotation.includes('Cigarettes'))).toBe(true);
  await expect(page.locator('article').last()).toContainText('earlier question');
});

test('scholarship renewal links the conditions and original scanned page', async ({page}) => {
  await page.goto('/');
  const result = await ask(page, 'If I have 7.6 CGPA will I be able to retain my scholarship?');
  expect(result.status).toBe('insufficient_evidence');
  await expect(page.locator('.answer > p').first()).toContainText('7.6 CGPA alone');
  await expect(page.locator('blockquote').first()).toContainText('program-specific CGPA');
  await expect(page.getByRole('link', {name: 'Scholarship Policy · Page 4'}).first()).toHaveAttribute('href', /\/pdf#page=4$/);
  await expect(page.locator('.note')).toContainText('Not independently verified');
  await page.getByText('View source details').click();
  await expect(page.getByText(/Scanned text/).first()).toBeVisible();
});

test('student scenarios show the retrieved rule and preserve its review status', async ({page}, testInfo) => {
  test.setTimeout(90000);
  await page.goto('/');
  const actual = [];
  for (const [question, term, followup] of [
    ['If I have 7.6 CGPA will I be able to retain my scholarship?', 'program-specific CGPA'],
    ['scholarship', 'scholarship'],
    ['smoke', 'cigarettes'],
    ['Can I smoke around the campus?', 'cigarettes'],
    ['What happens if I get caught with alcohol?', 'alcohol'],
    ['Can fighting lead to rustication?', 'rustication'],
    ["What if it's my second offence?", 'violence|rustication', true],
  ]) {
    if (actual.length && !followup) await page.getByRole('button', {name:'Start new conversation'}).click();
    const result = await ask(page, question);
    const answer = page.locator('.answer').last();
    await expect(answer.locator('.note')).toHaveText('Not independently verified · For reference only.');
    await expect(answer).toContainText(new RegExp(term,'i'));
    expect(result.status).toBe('insufficient_evidence');
    actual.push({question, message:await answer.locator(':scope > p').first().innerText(),
      sources:await answer.locator('a.chip').allInnerTexts(), status:result.status});
  }
  await testInfo.attach('student-questions', {body: JSON.stringify(actual,null,2), contentType:'application/json'});
  console.log(JSON.stringify(actual));
});

test('programme follow-up retains the grade and opens its original table page', async ({page})=>{
  await page.goto('/');
  const first='If I have 7.6 CGPA will I be able to retain my scholarship?';
  const original=await ask(page,first);
  const second=await ask(page,'My course is BTech AI.');
  const turn=page.locator('article').last();
  await expect(turn.getByRole('columnheader',{name:'Minimum CGPA Required'})).toBeVisible();
  await expect(turn.getByRole('cell',{name:'B. Tech AI',exact:true})).toBeVisible();
  await expect(turn.getByRole('cell',{name:'8.5 & above'})).toBeVisible();
  await expect(turn).toContainText('7.6 CGPA is below');
  await expect(turn.locator('.note')).toHaveText('Not independently verified · For reference only.');
  expect(second.status).toBe('insufficient_evidence');
  const link=turn.getByRole('link',{name:'Scholarship Policy · Page 4'});
  await expect(link).toHaveCount(1);
  await expect(link).toHaveAttribute('href',/\/pdf#page=4$/);
  const pdf=page.context().waitForEvent('response',r=>r.url().endsWith('/pdf') && r.status()===200);
  await link.click();
  expect((await pdf).headers()['content-type']).toBe('application/pdf');
  console.log(JSON.stringify({scholarshipConversation:[original.message,second.message]}));
  await ask(page,'My CGPA is actually 8.1.');
  await expect(page.locator('article').last()).toContainText('8.1 CGPA is below');
  await ask(page,'What about BTech CSE?');
  await expect(page.locator('article').last()).toContainText('8.1 CGPA is at or above');
});
