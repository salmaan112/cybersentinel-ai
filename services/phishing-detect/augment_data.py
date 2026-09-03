"""
Fixes a dataset bias discovered during testing: the original benign class
is dominated by bare homepage URLs (Alexa top-sites), so the model learned
'long URL path -> phishing', which wrongly flags real deep-link URLs like
GitHub repos or Wikipedia articles.

Fix: augment the benign class with real, legitimate deep-link URLs so the
model sees examples of long-but-safe paths during training.
"""
import pandas as pd
from features import extract_features

LEGIT_DEEP_LINKS = [
    "https://github.com/anthropics/claude-code",
    "https://github.com/pytorch/pytorch/blob/main/README.md",
    "https://en.wikipedia.org/wiki/Machine_learning",
    "https://en.wikipedia.org/wiki/Transport_Layer_Security",
    "https://stackoverflow.com/questions/12345678/how-to-fix-this-error",
    "https://docs.python.org/3/library/urllib.parse.html",
    "https://www.amazon.com/dp/B08N5WRWNW/ref=sr_1_3",
    "https://www.nytimes.com/2024/03/15/technology/ai-regulation-europe.html",
    "https://www.reddit.com/r/MachineLearning/comments/abc123/discussion_thread",
    "https://www.linkedin.com/in/some-professional-profile-12345",
    "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference",
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PL12345",
    "https://arxiv.org/abs/2401.12345",
    "https://www.google.com/maps/place/San+Francisco,+CA/@37.7749",
    "https://aws.amazon.com/blogs/machine-learning/deploying-models-at-scale/",
    "https://www.bbc.com/news/world-europe-12345678",
    "https://medium.com/@someauthor/understanding-neural-networks-abc123",
    "https://www.coursera.org/learn/machine-learning/lecture/week-1",
    "https://scholar.google.com/citations?user=abc123&hl=en",
    "https://www.microsoft.com/en-us/microsoft-365/blog/2024/03/15/new-features",
]


def main():
    df = pd.read_csv("data/phishing_small.csv")

    rows = []
    for url in LEGIT_DEEP_LINKS:
        feats = extract_features(url)
        feats["phishing"] = 0
        rows.append(feats)

    # Duplicate each a few times so they carry enough weight against 28k benign rows
    augmented = pd.DataFrame(rows * 15)

    # Only keep columns that exist in the original dataframe (drop network-dependent ones)
    keep_cols = [c for c in df.columns]
    augmented = augmented.reindex(columns=keep_cols, fill_value=0)

    combined = pd.concat([df, augmented], ignore_index=True)
    combined.to_csv("data/phishing_augmented.csv", index=False)
    print(f"Original rows: {len(df)}, Augmented rows added: {len(augmented)}, Total: {len(combined)}")


if __name__ == "__main__":
    main()
