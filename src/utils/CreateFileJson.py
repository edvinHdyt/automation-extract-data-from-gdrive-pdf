import os
def saveFile(data, path, file):
    with open(os.path.join(path, file), "a") as f:
        f.write(data)