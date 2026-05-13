import pandas as pd
import sqlite3

print("Running threshold recalibration...")

conn = sqlite3.connect('data/cpsc_recalls.db')

# load reviewer feedback
try:
    feedback = pd.read_sql("SELECT * FROM reviewer_feedback", conn)
except:
    print("No reviewer feedback found yet. Have reviewers confirm or reject some listings first.")
    conn.close()
    exit()

conn.close()

print(f"Total reviewer decisions: {len(feedback)}")
print(f"Confirmed matches: {len(feedback[feedback['reviewer_decision'] == 'CONFIRMED'])}")
print(f"False positives: {len(feedback[feedback['reviewer_decision'] == 'FALSE_POSITIVE'])}")

if len(feedback) < 10:
    print("\nNot enough feedback yet to recalibrate.")
    print("Need at least 10 reviewer decisions for meaningful recalibration.")
    print("Keep reviewing listings and run this script again later.")
else:
    # analyze what scores reviewers confirmed vs rejected
    confirmed = feedback[feedback['reviewer_decision'] == 'CONFIRMED']
    false_pos = feedback[feedback['reviewer_decision'] == 'FALSE_POSITIVE']

    print(f"\n--- SCORE ANALYSIS ---")
    print(f"Confirmed matches — avg score: {confirmed['confidence_score'].mean():.1f}")
    print(f"Confirmed matches — min score: {confirmed['confidence_score'].min():.1f}")
    print(f"False positives — avg score: {false_pos['confidence_score'].mean():.1f}")
    print(f"False positives — max score: {false_pos['confidence_score'].max():.1f}")

    # calculate recommended thresholds
    if len(confirmed) > 0 and len(false_pos) > 0:
        # HIGH threshold = lowest confirmed score minus small buffer
        recommended_high = max(50, confirmed['confidence_score'].min() - 5)
        # REVIEW threshold = highest false positive score plus small buffer
        recommended_review = min(recommended_high - 10, false_pos['confidence_score'].max() + 5)

        print(f"\n--- RECOMMENDED THRESHOLDS ---")
        print(f"Current:     HIGH >= 70    REVIEW >= 50")
        print(f"Recommended: HIGH >= {recommended_high:.0f}    REVIEW >= {recommended_review:.0f}")
        print(f"\nBased on {len(feedback)} reviewer decisions")
        print("Update these thresholds in matcher/matcher.py when you have 50+ decisions")

    # breakdown by hazard level
    print(f"\n--- FEEDBACK BY HAZARD LEVEL ---")
    print(feedback.groupby(['hazard_level', 'reviewer_decision']).size().to_string())

    # save summary to database
    summary = {
        'total_decisions': len(feedback),
        'confirmed': len(confirmed),
        'false_positives': len(false_pos),
        'avg_confirmed_score': round(confirmed['confidence_score'].mean(), 1) if len(confirmed) > 0 else 0,
        'avg_false_positive_score': round(false_pos['confidence_score'].mean(), 1) if len(false_pos) > 0 else 0
    }

    print(f"\n--- SUMMARY ---")
    for key, val in summary.items():
        print(f"{key}: {val}")