import threading
import time

def loop1():
    while True:
        print("1")
        time.sleep(1)

def loop2():
    while True:
        print("2")
        time.sleep(1)

if __name__ == "__main__":
    threads = []
    t1 = threading.Thread(target=loop1, daemon=True)
    t2 = threading.Thread(target=loop2, daemon=True)
    threads.extend([t1, t2])

    # start cả 2
    for t in threads:
        t.start()

    # join (sẽ chặn ở đây vì 2 vòng lặp vô tận)
    for t in threads:
        t.join()
