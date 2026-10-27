import os
def saveFile(data, path, file):
    with open(os.path.join(path, file), "w") as f:
        f.write(data)