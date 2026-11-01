# [요구사항 프롬프트로 전달될 내용]
# deep_get(data: dict, path: str, default=None) 함수를 구현하시오.
# path는 "user.address.zipcode" 형태의 점(dot)으로 구분된 문자열입니다.
# 중첩된 키를 따라 들어가 값을 반환하되, 중간에 키가 없거나 None이면 default 값을 반환해야 합니다.

def deep_get(data: dict, path: str, default=None):
    parts = path.split('.')
    for part in parts:
        if isinstance(data, dict):
         data = data.get(part)
        else:
            return default
    return data if data is not None else default
