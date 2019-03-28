import datetime
import re
import os
import pandas as pd
import pickle

expected_fn = re.compile(
    "([0-9]{4})-([0-9]{2})-([0-9]{2})_([a-zA-Z,]+)_collection.pickle")

def get_collections(directory="collections"):
    files = os.listdir(directory)
    matches = [expected_fn.match(file) for file in files]
    return pd.DataFrame([
        (file,
         datetime.date(year=int(m.group(1)),
                       month=int(m.group(2)),
                       day=int(m.group(3))),
         m.group(4),
         )
        for (m, file) in zip(matches, files) if m is not None
    ], columns=['file', 'date', 'groups'])

def get_latest_collection(directory="collections"):
    collections = get_collections(directory)
    latest_date = collections.date.max()

    fn = collections[collections.date == latest_date].file.iloc[0]
    return os.path.join(directory, fn)

def load_collection(path):
    with open(path, "rb") as fobj:
        return pickle.load(fobj)
