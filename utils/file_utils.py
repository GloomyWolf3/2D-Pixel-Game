def read_file(filename):
    with open(filename, 'r') as f:
        return f.read()

def write_file(filename, content):
    with open(filename, 'w') as f:
        f.write(content)

if __name__ == "__main__":
    content = "Hello, World!"
    write_file('test.txt', content)
    print(read_file('test.txt'))
    