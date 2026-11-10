"""Export reproducible demonstration query results to CSV."""
import argparse
import csv
import json
from datetime import date
from database import connect
from contextlib import closing
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def run(as_of='2023-12-31',patient_id=2):
    if date.fromisoformat(as_of).isoformat()!=as_of:
        raise ValueError('Use an ISO calendar date YYYY-MM-DD for --as-of')
    out=ROOT/'results';out.mkdir(exist_ok=True)
    with closing(connect(ROOT/'data/healthcare_demo.sqlite',readonly=True)) as con:
        for path in sorted((ROOT/'sql/queries').glob('*.sql')):
            cursor=con.execute(path.read_text(),{'as_of':as_of,'patient_id':patient_id})
            rows=cursor.fetchall()
            with (out/(path.stem+'.csv')).open('w',newline='') as f:
                writer=csv.writer(f,lineterminator="\n");writer.writerow([d[0] for d in cursor.description]);writer.writerows(rows)
            print(path.stem,len(rows),'result rows')
        context={
            'as_of':as_of,'patient_id':patient_id,
            'undated_orders_excluded':con.execute('SELECT COUNT(*) FROM MedicationOrder WHERE OrderDate IS NULL').fetchone()[0],
            'dated_orders_without_prescriber_excluded_from_query_08':con.execute('SELECT COUNT(*) FROM MedicationOrder WHERE OrderDate<=? AND PrescribingPhysicianID IS NULL',(as_of,)).fetchone()[0],
            'policy':'Date-filtered reports use recorded event dates, not historical versions of the chart. Undated orders are excluded, never assigned an invented date. Query 06 uses completed-stay snapshots. Narrative fields and care-team assignments are current records.'
        }
        (out/'report_context.json').write_text(json.dumps(context,indent=2)+'\n')



if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--as-of',default='2023-12-31')
    parser.add_argument('--patient-id',type=int,default=2)
    args=parser.parse_args();run(args.as_of,args.patient_id)
