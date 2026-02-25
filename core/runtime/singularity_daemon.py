"""
GemForge — Singularity Daemon (Horizon 3 Prototype)
Listens for production APM webhooks (Datadog/Sentry) and autonomously
triggers the Agentic Repair Loop to generate a fix and open a PR.
"""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime, timezone
import os

from core.runtime.logging import logger, setup_logging
from core.repair.agentic_loop import repair_node
from pipeline import git_publish_node
from state import create_initial_pipeline_state

class SingularityDaemonHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/webhook/incident":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                payload = json.loads(post_data.decode('utf-8'))
                logger.info(f"Received APM incident payload: {payload.get('incident_title')}")
                
                # Acknowledge receipt quickly so the APM doesn't timeout
                self.send_response(202)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "accepted", "message": "Singularity Daemon deploying fix sequence"}).encode())
                
                # Kick off the autonomous repair loop in the background
                threading.Thread(target=self._handle_incident, args=(payload,)).start()
                
            except json.JSONDecodeError:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Invalid JSON")
        else:
            self.send_response(404)
            self.end_headers()

    def _handle_incident(self, payload: dict):
        repo_path = payload.get("project_path")
        platform = payload.get("platform", "web")
        incident_title = payload.get("incident_title", "Unknown Incident")
        stack_trace = payload.get("stack_trace", "")
        
        if not repo_path or not os.path.exists(repo_path):
            logger.error(f"Singularity Daemon aborting: Valid project_path required. Received: {repo_path}")
            return

        logger.info(f"Initiating autonomous repair for {incident_title} in {repo_path}")
        
        # 1. Synthesize a PipelineState representing the broken production state
        raw_idea = f"Auto-Fix PR: {incident_title}"
        state = create_initial_pipeline_state(raw_idea=raw_idea)
        
        # Override state with incident context
        state["repo_path"] = repo_path
        state["selected_platform"] = platform
        
        # Inject the APM stack trace directly as if it were a failed test output
        state["test_report"] = f"PRODUCTION INCIDENT: {incident_title}

STACK TRACE:
{stack_trace}"
        state["test_details"] = stack_trace
        state["repair_count"] = 0
        state["repair_history"] = []
        
        # 2. Invoke the Surgeon (Agentic Loop)
        try:
            repair_result = repair_node(state)
            
            # Merge state 
            state.update(repair_result)
            
            if state.get("tests_passed"):
                logger.info(f"Surgeon successfully patched {incident_title}. Proceeding to auto-PR...")
                
                # 3. Publish the fix
                publish_result = git_publish_node(state)
                logger.info(f"Singularity Fix deployed: {publish_result.get('pr_url', 'Merged directly/Pushed')}")
            else:
                logger.warning(f"Surgeon failed to patch {incident_title} within budget/limits.")
                
        except Exception as e:
            logger.error(f"Singularity Daemon crashed during repair sequence: {e}", exc_info=True)


def run_daemon(port=8080):
    setup_logging()
    server_address = ('', port)
    httpd = HTTPServer(server_address, SingularityDaemonHandler)
    logger.info(f"Singularity Daemon listening on port {port}...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        logger.info("Singularity Daemon stopped.")

if __name__ == '__main__':
    run_daemon()
