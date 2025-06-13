Based on src/serializers/raw/ implementations refactor the ones in src/serializers/solid
following these premises:

1. All these parsers must pass the same tests as the ones in raw do
2. That means init, get and consume have to maintain the same api contract
3. Refactor in smaller classes and/or methods to keep the cognitive complexity under 14
4. Use SOLID Principles, Clean Code
5. Smaller methods and may now be annotated with @staticmethod
6. Smaller Classes may now be annotated with @dataclass
7. Pure-Function Deterministic approach, method become functions that are immutable when possible and thread-safe.
   Maximize statelessness
8. Hide and Encapsulate complexity as much as possible while improving readability. For example if and else clauses can
   become a check or validate methods
9. IT MUST INCREASE THE BIG O COMPLEXITY NOTATION OF THE RAW ALGORITHM
10. It should pass SonarQube, Snyk and Qodana Quality and Security gates.

I'm expecting changes on all 8 files within

guillermolam/DeepJudgeStreamingJsonBenchmark/tree/master/src/serializers/solid/