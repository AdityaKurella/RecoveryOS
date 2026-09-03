import csv
import random
from pathlib import Path


random.seed(42)


TRAIN_RATIO = 0.80


def load_features():
    input_path = (
        Path(__file__).parent.parent
        / "data"
        / "decision_features.csv"
    )

    with open(
        input_path,
        "r",
        newline="",
        encoding="utf-8",
    ) as file:
        return list(csv.DictReader(file))


def split_features(rows):
    rows = rows.copy()

    # Deterministic shuffle so every run produces
    # the same train/test split.
    random.shuffle(rows)

    split_index = int(
        len(rows) * TRAIN_RATIO
    )

    train_rows = rows[:split_index]
    test_rows = rows[split_index:]

    return train_rows, test_rows


def save_csv(rows, filename):
    output_path = (
        Path(__file__).parent.parent
        / "data"
        / filename
    )

    if not rows:
        raise ValueError(
            f"No rows available for {filename}"
        )

    fieldnames = rows[0].keys()

    with open(
        output_path,
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(rows)

    return output_path


def validate_split(
    all_rows,
    train_rows,
    test_rows,
):
    print(
        "\n========== TRAIN/TEST VALIDATION =========="
    )

    print(
        f"Total feature rows: {len(all_rows)}"
    )

    print(
        f"Training rows: {len(train_rows)}"
    )

    print(
        f"Test rows: {len(test_rows)}"
    )

    # -----------------------------------------
    # EXPECTED SPLIT
    # -----------------------------------------

    expected_train = int(
        len(all_rows) * TRAIN_RATIO
    )

    expected_test = (
        len(all_rows)
        - expected_train
    )

    print(
        f"Expected training rows: "
        f"{expected_train}"
    )

    print(
        f"Expected test rows: "
        f"{expected_test}"
    )

    # -----------------------------------------
    # COVERAGE
    # -----------------------------------------

    combined_count = (
        len(train_rows)
        + len(test_rows)
    )

    print(
        f"Split coverage: "
        f"{combined_count}/{len(all_rows)}"
    )

    # -----------------------------------------
    # DUPLICATE CHECK
    # -----------------------------------------

    train_ids = {
        row["failure_id"]
        for row in train_rows
    }

    test_ids = {
        row["failure_id"]
        for row in test_rows
    }

    overlap = train_ids.intersection(
        test_ids
    )

    print(
        f"Train/test overlapping IDs: "
        f"{len(overlap)}"
    )

    # -----------------------------------------
    # MISSING IDS
    # -----------------------------------------

    all_ids = {
        row["failure_id"]
        for row in all_rows
    }

    split_ids = (
        train_ids | test_ids
    )

    missing_ids = (
        all_ids - split_ids
    )

    print(
        f"Rows missing from split: "
        f"{len(missing_ids)}"
    )

    # -----------------------------------------
    # PERCENTAGES
    # -----------------------------------------

    if all_rows:

        train_percentage = (
            len(train_rows)
            / len(all_rows)
            * 100
        )

        test_percentage = (
            len(test_rows)
            / len(all_rows)
            * 100
        )

        print(
            f"\nTraining percentage: "
            f"{train_percentage:.2f}%"
        )

        print(
            f"Test percentage: "
            f"{test_percentage:.2f}%"
        )

    # -----------------------------------------
    # FINAL STATUS
    # -----------------------------------------

    valid = (
        len(train_rows) == expected_train
        and len(test_rows) == expected_test
        and len(overlap) == 0
        and len(missing_ids) == 0
        and combined_count == len(all_rows)
    )

    if valid:
        print(
            "\nSplit validation: PASSED ✅"
        )
    else:
        print(
            "\nSplit validation: FAILED ❌"
        )

    print(
        "==========================================="
    )


if __name__ == "__main__":

    features = load_features()

    train_rows, test_rows = split_features(
        features
    )

    train_path = save_csv(
        train_rows,
        "train_features.csv",
    )

    test_path = save_csv(
        test_rows,
        "test_features.csv",
    )

    print(
        f"Training dataset saved to: "
        f"{train_path}"
    )

    print(
        f"Test dataset saved to: "
        f"{test_path}"
    )

    validate_split(
        features,
        train_rows,
        test_rows,
    )