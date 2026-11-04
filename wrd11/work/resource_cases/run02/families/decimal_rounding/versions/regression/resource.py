import sys, json
from decimal import Decimal, ROUND_HALF_UP
def transform(item):
    return format(Decimal(float(item['value'])).quantize(Decimal('0.01'),rounding=ROUND_HALF_UP),'.2f')

if __name__ == "__main__":
    data = json.loads(sys.stdin.read())
    print(json.dumps([transform(x) for x in data], ensure_ascii=False, sort_keys=True))
