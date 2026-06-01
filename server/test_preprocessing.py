from preprocessing.preprocess import run_preprocessing


def main():
    master_df, report = run_preprocessing()

    print("\n=== MASTER DATASET ===")
    print(master_df.head())

    print("\n=== SHAPE ===")
    print(master_df.shape)

    print("\n=== REPORT ===")
    print(report)


if __name__ == "__main__":
    main()