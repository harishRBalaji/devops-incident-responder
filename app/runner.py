import time, json
from rich import print
from app.config import POLL_INTERVAL_SECONDS
from app.db.dal import init_db, get_open_incidents, mark_in_progress, record_step
from app.agents.collector_agent import collector_run
from app.agents.analyst_agent import analyze_logs
from app.agents.supervisor import supervisor_orchestrate

def process_one(incident):
    print(f"[bold cyan]Processing incident {incident['id']}[/]")
    mark_in_progress(incident['id'])
    record_step(incident['id'], 'supervisor', 'start', 'Supervisor started')
    collected = collector_run(incident)
    analysis = analyze_logs(incident, collected)
    supervisor_orchestrate(incident, analysis)

def main():
    init_db()
    print("[green]Agent loop started[/]")
    while True:
        incidents = get_open_incidents()
        for inc in incidents:
            try:
                process_one(inc)
            except Exception as e:
                record_step(inc['id'], 'supervisor', 'error', f'Error: {e}')
        time.sleep(POLL_INTERVAL_SECONDS)

if __name__ == '__main__':
    main()
