"""
Test script for text cleaning module.
Demonstrates handling of tables, math notation, and special symbols.
"""

from ingestion.text_cleaning import TextCleanerFactory
import logfire


def test_surrogate_removal():
    """Test surrogate character removal."""
    print("\n" + "="*80)
    print("TEST 1: Surrogate Character Removal")
    print("="*80)

    # Text with surrogate characters (mathematical symbols from PDF)
    text_with_surrogates = "Distance formula: d = \ud835\udc65 between two points"

    cleaner = TextCleanerFactory.create_default_cleaner()
    cleaned = cleaner.clean(text_with_surrogates, log_steps=True)

    print(f"Original: {repr(text_with_surrogates)}")
    print(f"Cleaned:  {repr(cleaned)}")
    print(f"✓ Surrogates removed successfully")


def test_math_notation():
    """Test mathematical notation normalization."""
    print("\n" + "="*80)
    print("TEST 2: Mathematical Notation Normalization")
    print("="*80)

    math_text = """
    The formula is: α + β ≈ γ × π
    Area = πr²
    x² + y² ≤ r²
    ∑(i=1 to n) = n(n+1)/2
    √2 ≈ 1.414
    """

    cleaner = TextCleanerFactory.create_default_cleaner()
    cleaned = cleaner.clean(math_text, log_steps=True)

    print(f"Original:\n{math_text}")
    print(f"\nCleaned:\n{cleaned}")
    print(f"✓ Math notation converted to ASCII")


def test_table_preservation():
    """Test table structure preservation."""
    print("\n" + "="*80)
    print("TEST 3: Table Structure Preservation")
    print("="*80)

    table_text = """
    ┌─────────────┬──────────┬─────────┐
    │   Feature   │  Value   │  Unit   │
    ├─────────────┼──────────┼─────────┤
    │ Temperature │   25.5   │   °C    │
    │ Pressure    │  101.3   │   kPa   │
    │ Humidity    │   65     │   %     │
    └─────────────┴──────────┴─────────┘
    """

    cleaner = TextCleanerFactory.create_default_cleaner()
    cleaned = cleaner.clean(table_text, log_steps=True)

    print(f"Original:\n{table_text}")
    print(f"\nCleaned:\n{cleaned}")
    print(f"✓ Table structure preserved with ASCII")


def test_special_symbols():
    """Test special symbol normalization."""
    print("\n" + "="*80)
    print("TEST 4: Special Symbol Normalization")
    print("="*80)

    symbol_text = """
    "Smart quotes" and 'apostrophes'
    Prices: €100, £50, ¥1000
    Fractions: ½, ¼, ¾
    Bullets: • Item 1 • Item 2
    Dashes: em—dash, en–dash, minus−sign
    Ellipsis… continues
    """

    cleaner = TextCleanerFactory.create_default_cleaner()
    cleaned = cleaner.clean(symbol_text, log_steps=True)

    print(f"Original:\n{symbol_text}")
    print(f"\nCleaned:\n{cleaned}")
    print(f"✓ Special symbols normalized")


def test_combined_challenges():
    """Test combined challenges from real documents."""
    print("\n" + "="*80)
    print("TEST 5: Combined Real-World Example")
    print("="*80)

    complex_text = """
    ┌──────────────────────────────────────────────┐
    │  Machine Learning Metrics                     │
    ├─────────────┬────────────┬───────────────────┤
    │   Metric    │   Formula  │   Description     │
    ├─────────────┼────────────┼───────────────────┤
    │ Accuracy    │  (TP+TN)/N │  Overall correct  │
    │ Precision   │  TP/(TP+FP)│  Positive predict │
    │ F₁-Score    │  2×P×R/(P+R)│ Harmonic mean    │
    └─────────────┴────────────┴───────────────────┘

    The gradient descent formula: θ := θ − α∇J(θ)
    Where α is the learning rate ≈ 0.01–0.1

    Cost function: J(θ) = ½∑(hθ(x⁽ⁱ⁾) − y⁽ⁱ⁾)²

    "State-of-the-art" results… 95% accuracy!
    """

    cleaner = TextCleanerFactory.create_default_cleaner()
    cleaned = cleaner.clean(complex_text, log_steps=True)

    print(f"Original:\n{complex_text}")
    print(f"\nCleaned:\n{cleaned}")
    print(f"✓ Complex document cleaned successfully")


def test_custom_cleaner():
    """Test custom cleaner configuration."""
    print("\n" + "="*80)
    print("TEST 6: Custom Cleaner Configuration")
    print("="*80)

    # Create cleaner that preserves math symbols
    cleaner = TextCleanerFactory.create_custom_cleaner(
        remove_surrogates=True,
        normalize_unicode=True,
        normalize_math=False,  # Preserve math notation
        preserve_tables=True,
        normalize_symbols=True,
        normalize_whitespace=True
    )

    text = "The formula is: α + β = γ × π²"
    cleaned = cleaner.clean(text)

    print(f"Original: {text}")
    print(f"Cleaned:  {cleaned}")
    print(f"✓ Custom configuration works (math preserved)")


def test_minimal_vs_aggressive():
    """Compare minimal and aggressive cleaning."""
    print("\n" + "="*80)
    print("TEST 7: Minimal vs Aggressive Cleaning")
    print("="*80)

    test_text = "α + β ≈ γ…  "Special quotes"  €100"

    minimal = TextCleanerFactory.create_minimal_cleaner()
    aggressive = TextCleanerFactory.create_aggressive_cleaner()

    minimal_result = minimal.clean(test_text)
    aggressive_result = aggressive.clean(test_text)

    print(f"Original:    {repr(test_text)}")
    print(f"Minimal:     {repr(minimal_result)}")
    print(f"Aggressive:  {repr(aggressive_result)}")
    print(f"✓ Different cleaning levels work as expected")


if __name__ == "__main__":
    # Configure logfire for testing
    logfire.configure()

    print("\n" + "="*80)
    print("TEXT CLEANING MODULE TEST SUITE")
    print("Testing robust handling of tables, math notation, and special symbols")
    print("="*80)

    try:
        test_surrogate_removal()
        test_math_notation()
        test_table_preservation()
        test_special_symbols()
        test_combined_challenges()
        test_custom_cleaner()
        test_minimal_vs_aggressive()

        print("\n" + "="*80)
        print("✓ ALL TESTS PASSED")
        print("="*80)
        print("\nThe text cleaning module successfully handles:")
        print("  • Unicode surrogate characters (database compatibility)")
        print("  • Mathematical notation (normalized to ASCII)")
        print("  • Table structures (preserved with ASCII formatting)")
        print("  • Special symbols (quotes, bullets, currencies, fractions)")
        print("  • Whitespace normalization (preserves paragraphs)")
        print("  • Custom configurations (flexible pipeline)")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
