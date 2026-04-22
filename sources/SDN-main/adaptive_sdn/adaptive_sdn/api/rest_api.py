from ryu.app.wsgi import ControllerBase, route
from webob import Response
import json

INTENTS = []
CONTEXT = {}

class IntentAPI(ControllerBase):
    def __init__(self, req, link, data, **config):
        super(IntentAPI, self).__init__(req, link, data, **config)
        self.controller = data['controller']

    # -------------------------------------------------------------
    # 1. POST /api/intent/submit
    # -------------------------------------------------------------
    @route('intent', '/api/intent/submit', methods=['POST'])
    def submit_intent(self, req, **kwargs):
        try:
            body = json.loads(req.body.decode('utf-8'))
            intent = body.get("intent")

            if intent is None:
                return Response(
                    status=400,
                    content_type='application/json; charset=utf-8',
                    body=json.dumps({"error": "intent missing"})
                )

            INTENTS.append(intent)
            print("### NEW INTENT RECEIVED:", intent)

            return Response(
                content_type='application/json; charset=utf-8',
                body=json.dumps({"status": "OK", "received": intent})
            )
        except Exception as e:
            return Response(
                status=500,
                content_type='application/json; charset=utf-8',
                body=json.dumps({"error": str(e)})
            )

    # -------------------------------------------------------------
    # 2. POST /api/context/update
    # -------------------------------------------------------------
    @route('context', '/api/context/update', methods=['POST'])
    def update_context(self, req, **kwargs):
        try:
            body = json.loads(req.body.decode('utf-8'))
            CONTEXT.update(body)

            print("### CONTEXT UPDATED:", CONTEXT)

            return Response(
                content_type='application/json; charset=utf-8',
                body=json.dumps({"status": "updated", "context": CONTEXT})
            )
        except Exception as e:
            return Response(
                status=500,
                content_type='application/json; charset=utf-8',
                body=json.dumps({"error": str(e)})
            )

    # -------------------------------------------------------------
    # 3. GET /api/metrics/get
    # -------------------------------------------------------------
    @route('metrics', '/api/metrics/get', methods=['GET'])
    def get_metrics(self, req, **kwargs):
        return Response(
            content_type='application/json; charset=utf-8',
            body=json.dumps({"context": CONTEXT})
        )

    # -------------------------------------------------------------
    # 4. POST /api/flows/apply
    # -------------------------------------------------------------
    @route('flows', '/api/flows/apply', methods=['POST'])
    def apply_flow(self, req, **kwargs):
        try:
            body = json.loads(req.body.decode('utf-8'))
            print("### FLOW APPLY REQUEST:", body)

            return Response(
                content_type='application/json; charset=utf-8',
                body=json.dumps({"status": "flow-request-received"})
            )
        except Exception as e:
            return Response(
                status=500,
                content_type='application/json; charset=utf-8',
                body=json.dumps({"error": str(e)})
            )
