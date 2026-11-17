import multiprocessing

if __name__ == "__main__":
    multiprocessing.freeze_support()
    from src.app import main
    raise SystemExit(main())
