"""Read-only, answer-free publication planning against an explicit source checkout.

This never publishes, initializes Flask, migrates, or exports keyed candidates.
The output is a proposal, not an editorial approval or equivalence decision.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import sys


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def inventory(db, original_decisions, foundation_decisions):
    from club.skill_content import CASES, candidate_form, lesson_id
    from club.foundation_content import CASES as FOUNDATIONS, lesson_body
    from club.skills import validate_form

    db.row_factory = sqlite3.Row
    graph = json.loads(db.execute('SELECT r.body FROM skill_releases r JOIN skill_active a ON a.release_id=r.id').fetchone()[0])
    result = dict(active_release=graph['release'], publication_performed=False,
                  counts={table: db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0] for table in
                          ['skill_forms', 'skill_practical_tasks', 'skill_evidence', 'skill_application_evidence']}, candidates=[])
    for family, cases in [('original', CASES), ('foundation', FOUNDATIONS)]:
        for case in cases:
            form = candidate_form(case)
            identity = ('skill-example-form-' if family == 'original' else 'skill-foundation-form-')+case['slug']+'-v1'
            row = db.execute('''SELECT l.body,l.access,l.status,c.id AS course_id,c.status AS course_status
                FROM lessons l JOIN modules m ON m.id=l.module_id JOIN courses c ON c.id=m.course_id
                WHERE l.id=?''', (lesson_id(case),)).fetchone()
            blockers = []
            if not row or row['body'] != lesson_body(case):
                blockers.append('Persisted source missing or differs from reviewed candidate')
            if not row or row['status'] != 'published' or row['course_status'] != 'published':
                blockers.append('Source lesson/course unavailable')
            if not any(m['objective_id'] == case['objective'] and m['lesson_id'] == lesson_id(case) for m in graph['mappings']):
                blockers.append('Source is not mapped in active graph')
            reviewed = []
            for item in form['items']:
                if family == 'foundation':
                    matches = [d for d in foundation_decisions if d['form_id'] == identity and d['item_id'] == item['id']]
                    valid = len(matches) == 1 and all([
                        matches[0]['form_sha256'] == digest(form), matches[0]['source'] == item['source'],
                        matches[0]['answer'] == item['answer'], matches[0]['objective_id'] == item['objective_id'],
                        matches[0]['decision'] == 'acceptable_for_narrow_taught_case_understanding'])
                else:
                    matches = [d for d in original_decisions if d['case'] == case['slug'] and d['item'] == item['id']]
                    valid = len(matches) == 1 and all([
                        matches[0]['sha256'] == item['source']['sha256'], matches[0]['paragraph'] == item['source']['paragraph'],
                        matches[0]['source_edition'] == item['source']['edition'], matches[0]['answer_id'] == item['answer'],
                        matches[0]['objective'] == item['objective_id'], matches[0]['lineage'] == item['lineage_id'],
                        matches[0]['decision'] == 'acceptable_for_narrow_scenario_understanding'])
                if not valid:
                    blockers.append('Missing or mismatched item decision: '+item['id'])
                reviewed.append(dict(item_id=item['id'], source_sha256=item['source']['sha256'],
                                     paragraph=item['source']['paragraph'], edition=item['source']['edition'], decision_matches=valid))
            if family == 'original':
                blockers.append('Original audit pins sources/keys/lineage, not full form hash; exact form confirmation required')
            thresholds = validate_form(form, graph)
            result['candidates'].append(dict(id=identity, family=family, node_id=case['objective'],
                form_sha256=digest(form), suggested_initial_selection=(family == 'foundation' and case['slug'].endswith('-a') and not blockers), lesson_id=lesson_id(case), lesson_url='/lessons/'+lesson_id(case),
                course_id=row['course_id'] if row else None, proposed_access=row['access'] if row else None,
                source_body_sha256=hashlib.sha256(row['body'].encode()).hexdigest() if row else None,
                thresholds=thresholds, items=reviewed, blockers=blockers,
                disposition='hold' if blockers else 'eligible_for_explicit_narrow_scope_editorial_selection',
                scope=form['scope'], applied_credit=False, retake_equivalence='not_approved',
                publication_requires='Named editor and manager scheduling; select one foundation case per objective, not interchangeable A/B retakes'))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--database', type=Path, required=True)
    parser.add_argument('--original-decisions', type=Path, required=True)
    parser.add_argument('--foundation-decisions', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.source_root.resolve()))
    with sqlite3.connect(args.database.resolve().as_uri()+'?mode=ro', uri=True) as db:
        db.execute('PRAGMA query_only=ON')
        db.execute('BEGIN')
        report = inventory(db, json.loads(args.original_decisions.read_text()), json.loads(args.foundation_decisions.read_text()))
    report['source_root'] = str(args.source_root.resolve())
    report['review_files'] = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in
                              [args.original_decisions, args.foundation_decisions]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(dict(counts=report['counts'], candidates=len(report['candidates']),
                         matching_foundation_candidates=sum(not c['blockers'] for c in report['candidates']))))


if __name__ == '__main__':
    main()
