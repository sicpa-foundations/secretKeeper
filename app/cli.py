import inspect
from typing import get_origin, get_args, Annotated, Union

import inquirer

from app.celery_app import app

# ANSI color codes
GREEN = "\033[92m"
RESET = "\033[0m"


def prompt_for_arg(name, param):
    hint = ""
    if get_origin(param.annotation) is Annotated:
        param_type, *meta = get_args(param.annotation)
        hint = meta[0] if meta else ""

    default_val = param.default if param.default is not inspect.Parameter.empty else None
    param_type_str = type_to_str(param.annotation)

    # Print argument name in green
    print(f"{GREEN}{name}{RESET}")

    # Print type, default, hint
    print(f"Type: {param_type_str}, Default: {default_val}, desc: {hint}")

    # Input prompt
    val = input("Enter value (leave empty to skip): ")

    if val == "":
        return None  # Will be skipped in Celery call

    return cast_input(val, param.annotation)


def type_to_str(tp):
    if get_origin(tp) is Annotated:
        tp, *_ = get_args(tp)
    origin = get_origin(tp)
    if origin is Union:
        return " or ".join(t.__name__ if hasattr(t, "__name__") else str(t) for t in get_args(tp))
    return tp.__name__ if hasattr(tp, "__name__") else str(tp)


def cast_input(value, tp):
    if get_origin(tp) is Annotated:
        tp, *_ = get_args(tp)
    origin = get_origin(tp)
    if origin is Union:
        non_none = [t for t in get_args(tp) if t is None]
        tp = non_none[0] if non_none else str
    if tp is bool:
        return value.lower() in ("1", "true", "yes", "y")
    if tp is int:
        return int(value)
    if tp is float:
        return float(value)
    return value


def collect_args(task):
    kwargs = {}
    fn = getattr(task.run, "__wrapped__", task.run)
    sig = inspect.signature(fn)

    for name, param in sig.parameters.items():
        val = prompt_for_arg(name, param)
        if val is not None:  # Only include if user provided input
            kwargs[name] = val

    return kwargs


def run_cli():
    # Filter out built-in Celery tasks
    tasks = {k: v for k, v in app.tasks.items() if not k.startswith("celery.")}

    if not tasks:
        print("No custom tasks found.")
        return

    # Interactive task selection
    task_name = inquirer.list_input("Select a task to run:", choices=list(tasks.keys()))
    task = tasks[task_name]

    # Collect args
    args = collect_args(task)
    result = task.apply_async(kwargs=args)
    print(f"Task {task.name} added to the queue. Task ID: {result.id}")


if __name__ == "__main__":
    run_cli()
