import datetime as dt
from pickle import dumps as d
import pickle

pickle.DEFAULT_PROTOCOL = 5

a = [dt.datetime(10, 10, 10, 10, 10, 10, 10, dt.timezone.utc), dt.datetime(10, 10, 10, 10, 10, 10, 10, dt.timezone.utc)]

b = [dt.datetime(10, 10, 10, 10, 10, 10, 10, dt.timezone.utc)]
b.append(dt.datetime(10, 10, 10, 10, 10, 10, 10, dt.timezone.utc))
b.extend([dt.datetime.max] * 100)
b = b[:2]

# Works
print(a == b, d(a) == d(b))


a = [1, 2, 3]
b = [1, 2] + [3]

print(a == b, d(a) == d(b))