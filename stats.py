import jsonlines
from tabulate import tabulate
import math

class Welford(object):
    def __init__(self,lst=None):
        self.k = 0
        self.M = 0
        self.S = 0

        self.__call__(lst)

    def update(self,x):
        if x is None:
            return
        self.k += 1
        newM = self.M + (x - self.M)*1./self.k
        newS = self.S + (x - self.M)*(x - newM)
        self.M, self.S = newM, newS
        return self

    def consume(self,lst):
        lst = iter(lst)
        for x in lst:
            self.update(x)

    def __call__(self,x):
        if hasattr(x,"__iter__"):
            self.consume(x)
        else:
            self.update(x)

    @property
    def mean(self):
        return self.M
    @property
    def meanfull(self):
        return self.mean, self.std/math.sqrt(self.k)
    @property
    def std(self):
        if self.k==1:
            return 0
        return math.sqrt(self.S/(self.k-1))
    def __repr__(self):
        return "<Welford: {} +- {}>".format(self.mean, self.std)

data = {}

with jsonlines.open('/tmp/fhir/Observation.json') as reader:
    for obj in reader:
        key = obj['code']['coding'][0]['system'] + "|" + obj['code']['coding'][0]['code']
        display = obj['code']['coding'][0]['display']
        prev = data.get(key, {'count': 0, 'w': Welford()})
        if 'valueQuantity' in obj and 'value' in obj['valueQuantity']:
            value = obj['valueQuantity']['value']
            data[key] = {'display': display, 'count': prev['count'] + 1, 'w': prev['w'].update(value)}

table = []
for key,value in data.items():
    table.append([value['display'], value['w'].mean, value['w'].std, value['count'], key])

table = sorted(table, key = lambda x: x[0])
table = [row for row in table if row[3] >= 100]

with open('/tmp/output/table.txt', 'w') as output:
    print(tabulate(table, headers=['name', 'mean', 'std', 'count', 'code'], tablefmt="fancy_grid", floatfmt=".2f"), file=output)

cohort_key = 'http://loinc.org|2339-0'

patients = set()
with jsonlines.open('/tmp/fhir/Observation.json') as reader:
    for obj in reader:
        key = obj['code']['coding'][0]['system'] + "|" + obj['code']['coding'][0]['code']
        if key == cohort_key and 'valueQuantity' in obj and 'value' in obj['valueQuantity']:
            w = data[key]['w']
            value = obj['valueQuantity']['value']
            if value > w.mean + 2 * w.std:
                patients.add(obj['subject']['reference'].split('/')[1])

with open('/tmp/output/cohort.csv', 'w') as output:
    print('cohortName,patientId', file=output)
    for patient in patients:
        print('Glucose Bld Qn (POC),{}'.format(patient), file=output)
