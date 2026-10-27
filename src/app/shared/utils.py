from yaml import SafeDumper, ScalarNode

class PypoDumper(SafeDumper):
    pass

def _str_presenter(dumper: SafeDumper, data: str) -> ScalarNode:
    if '\n' in data or len(data.splitlines()) > 1:
        lines = [line.rstrip() for line in data.splitlines()]
        data = '\n'.join(lines) + '\n'
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)

PypoDumper.add_representer(str, _str_presenter)

def normalize_model_name(model_name: str) -> tuple[str, str]:
    pass
