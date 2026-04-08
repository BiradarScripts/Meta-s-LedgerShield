import json
from server.grading import score_submission
with open("live_model_comparison_debug/gpt-5.4/CASE-B-005.json") as f:
    data = json.load(f)

case_context = {
    "case_snapshot": {
        "case_id": "CASE-B-005"
    }
}
with open("server/fixtures/cases.json") as f:
    cases = json.load(f)

gold = next(c["gold"] for c in cases if c["case_id"] == "CASE-B-005")

submission = data["final_submission"]
score, breakdown = score_submission(
    task_type="task_b",
    submitted=submission,
    gold=gold,
    trajectory=data["system_state"]["trajectory"],
    case_context=case_context
)
print(f"Score: {score}")
