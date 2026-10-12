1. The naive prompt, `fix validation in add`, did not specify the exact validation rules, required test cases, or a strict file-change limit.
2. The naive run expanded scope by adding extra invalid-date and invalid-amount-text handling, beyond the intended requirements.
3. In Round 2, the brief's explicit rules, required four tests in `tests/test_cli.py`, and "Do not change any other file" constraint kept the implementation focused.
