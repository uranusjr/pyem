__all__ = ["run"]


def run(project, options):
    if options.spec:
        runtime = project.find_runtime(options.spec)
    else:
        runtime = project.get_active_runtime()
    if not runtime:
        raise Exception("no runtime")
    print(f"run in {runtime.name}:", options.cmd, *options.args)
