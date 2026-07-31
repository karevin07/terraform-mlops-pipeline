#!/usr/bin/env python3
"""Promote / rollback / list model versions in DynamoDB registry."""
import argparse
import os
import sys

# Allow `uv run python scripts/promote_model.py ...` from repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import boto3
from boto3.dynamodb.conditions import Key

from scripts.promote_logic import plan_promote, plan_rollback

DEFAULT_MODEL = "stock-prediction"


def get_table():
    table_name = os.environ.get("DYNAMODB_TABLE")
    if not table_name:
        raise SystemExit("DYNAMODB_TABLE env var is required")
    region = os.environ.get("AWS_REGION", "us-east-1")
    return boto3.resource("dynamodb", region_name=region).Table(table_name)


def get_item(table, model_name, version):
    resp = table.get_item(Key={"ModelName": model_name, "Version": version})
    return resp.get("Item")


def find_stable_version(table, model_name):
    resp = table.query(
        KeyConditionExpression=Key("ModelName").eq(model_name),
        ScanIndexForward=False,
        Limit=50,
    )
    for item in resp.get("Items", []):
        if item.get("Status") == "stable":
            return item["Version"]
    return None


def apply_actions(table, model_name, actions, dry_run=False):
    for action in actions:
        print(f"{'[dry-run] ' if dry_run else ''}SET {model_name} {action['version']} -> {action['status']}")
        if dry_run:
            continue
        table.update_item(
            Key={"ModelName": model_name, "Version": action["version"]},
            UpdateExpression="SET #S = :s",
            ExpressionAttributeNames={"#S": "Status"},
            ExpressionAttributeValues={":s": action["status"]},
        )


def cmd_list(table, model_name, limit):
    resp = table.query(
        KeyConditionExpression=Key("ModelName").eq(model_name),
        ScanIndexForward=False,
        Limit=limit,
    )
    for item in resp.get("Items", []):
        metrics = item.get("Metrics", "{}")
        print(f"{item['Version']}\t{item.get('Status')}\t{metrics}")


def cmd_promote(table, model_name, version, dry_run=False):
    item = get_item(table, model_name, version)
    target_status = item.get("Status") if item else None
    current = find_stable_version(table, model_name)
    actions = plan_promote(version, target_status, current)
    if not actions:
        print(f"{version} already stable; nothing to do")
        return
    apply_actions(table, model_name, actions, dry_run=dry_run)


def cmd_rollback(table, model_name, version, dry_run=False):
    item = get_item(table, model_name, version)
    target_status = item.get("Status") if item else None
    current = find_stable_version(table, model_name)
    actions = plan_rollback(version, target_status, current)
    if not actions:
        print(f"{version} already stable; nothing to do")
        return
    apply_actions(table, model_name, actions, dry_run=dry_run)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Model registry promote/rollback")
    parser.add_argument("--model-name", default=DEFAULT_MODEL)
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list")
    p_list.add_argument("--limit", type=int, default=20)

    p_prom = sub.add_parser("promote")
    p_prom.add_argument("--version", required=True)
    p_prom.add_argument("--dry-run", action="store_true")

    p_rb = sub.add_parser("rollback")
    p_rb.add_argument("--version", required=True)
    p_rb.add_argument("--dry-run", action="store_true")

    args = parser.parse_args(argv)
    table = get_table()
    if args.command == "list":
        cmd_list(table, args.model_name, args.limit)
    elif args.command == "promote":
        cmd_promote(table, args.model_name, args.version, dry_run=args.dry_run)
    elif args.command == "rollback":
        cmd_rollback(table, args.model_name, args.version, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
