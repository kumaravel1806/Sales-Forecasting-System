import time

if __name__ == "__main__":
    print("Worker placeholder running. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        print("Worker stopped.")
