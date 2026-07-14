pants generate-lockfiles
pants lint check src/ test/
pants test --output=all --test-force --use-coverage --report test/::