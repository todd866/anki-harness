#!/usr/bin/env python3
"""Run scenarios on several Anki versions and say where the versions disagree.

    ./install.sh 26.9.4 && ./install.sh 26.11b1      # once per version
    python3 run.py [--versions 26.9.4,26.11b1] [--scenarios review_keys,...] [--collection PATH]

Each (version, scenario) runs in its own process, inside that version's own environment.
Results go to $ANKI_HARNESS_HOME/runs/<run>/<version>/<scenario>/result.json
(ANKI_HARNESS_HOME defaults to ~/.local/state/anki-harness).

What it reports:
  FAIL     a check a scenario says must hold on every version did not hold
  DIFFERS  an observation is not the same on every version that ran (a regression, a fix, or
           noise: read it before believing it)
  known    a check tied to an open upstream issue still fails: expected, not a finding
  FIXED?   a check tied to an open upstream issue now passes: worth telling the maintainers
  inconclusive  a scenario's own control failed three times running: the harness could not
           drive Anki, so nothing is concluded
"""
import argparse
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.environ.get("ANKI_HARNESS_HOME") or os.path.expanduser("~/.local/state/anki-harness")


def python_for(version: str) -> str:
    env = os.path.join(STATE, f"env-{version}", "bin", "python")
    if os.path.exists(env):
        return env
    sys.exit(f"no environment for Anki {version}: run ./install.sh {version}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--versions", default="26.9.4,26.11b1")
    parser.add_argument("--scenarios", default="")
    parser.add_argument("--collection", default="")
    parser.add_argument("--timeout", type=int, default=150)
    args = parser.parse_args()
    versions = args.versions.split(",")
    available = sorted(f[:-3] for f in os.listdir(os.path.join(HERE, "harness", "scenarios")) if f.endswith(".py") and not f.startswith("_"))
    scenarios = args.scenarios.split(",") if args.scenarios else available
    run_dir = os.path.join(STATE, "runs", time.strftime("%Y%m%d-%H%M%S"))
    results: dict = {}
    for scenario in scenarios:
        for index, version in enumerate(versions):
            out = os.path.join(run_dir, version, scenario)
            os.makedirs(out, exist_ok=True)
            command = [python_for(version), "-m", "harness.inproc", scenario, out] + ([args.collection] if args.collection else [])
            env = dict(os.environ, HARNESS_CDP_PORT=str(9400 + index), HARNESS_HARD_TIMEOUT_S=str(args.timeout - 10))
            path = os.path.join(out, "result.json")
            for attempt in range(1, 4):  # a run whose own control failed says nothing: try again
                if os.path.exists(path):
                    os.rename(path, f"{path}.attempt{attempt - 1}")
                with open(os.path.join(out, "process.log"), "a") as log:
                    try:
                        code = subprocess.run(command, cwd=HERE, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=args.timeout).returncode
                    except subprocess.TimeoutExpired:
                        code = -1
                result = json.load(open(path)) if os.path.exists(path) else {"status": "crashed" if code != -1 else "hung", "observations": {}, "checks": [], "error": f"exit {code}; see {out}/process.log"}
                result["attempts"] = attempt
                if result["status"] != "inconclusive":
                    break
            results[(scenario, version)] = result

    findings = 0
    for scenario in scenarios:
        print(f"\n== {scenario}")
        per = {v: results[(scenario, v)] for v in versions}
        for version, result in per.items():
            failed = [c for c in result["checks"] if not c["ok"]]
            again = f" (attempt {result['attempts']})" if result.get("attempts", 1) > 1 else ""
            print(f"  {version:9} {result['status']:8} {len(result['checks']) - len(failed)}/{len(result['checks'])} checks{again}")
            if result["status"] != "ran":
                findings += 1
                print(f"      {result.get('error', '').strip().splitlines()[-1] if result.get('error') else ''}")
            for check in result["checks"]:
                known = check.get("known")
                if check["ok"] and known:
                    findings += 1
                    print(f"      FIXED?  {known} no longer reproduces: {check['name']}")
                elif not check["ok"] and known:
                    print(f"      known {known} still present: {check['detail']}")
                elif not check["ok"]:
                    findings += 1
                    print(f"      FAIL  {check['name']}: {check['detail']}")
        names: list = []
        ran = [v for v in versions if per[v]["status"] == "ran"]
        for result in per.values():
            names += [n for n in result["observations"] if n not in names]
        for name in names:
            values = {v: json.dumps(per[v]["observations"].get(name, "<absent>"), sort_keys=True, default=str) for v in ran}
            if len(set(values.values())) > 1:
                findings += 1
                print(f"      DIFFERS  {name}")
                for version, value in values.items():
                    print(f"          {version:9} {value[:160]}")
    print(f"\n{findings} finding(s) · {run_dir}")
    json.dump({f"{s}|{v}": r for (s, v), r in results.items()}, open(os.path.join(run_dir, "summary.json"), "w"), indent=1, default=str)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
