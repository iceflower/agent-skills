---
name: testing
description: >-
  BDD-style test writing rules including unit testing patterns, integration
  testing with Testcontainers, contract testing for microservices (Pact,
  Spring Cloud Contract), and performance testing strategies (k6, Gatling).
  Use when writing or modifying test code.
---
# BDD-Style Unit Test Rules

## 1. BDD Style Required

- Always use BDD style (Describe - Context - It)
- Use English naming for test blocks with Korean descriptions

## 2. Naming Conventions

| Block | Pattern | Example |
| --- | --- | --- |
| `describe` (class) | `{ClassName} 클래스의` | `AuthFacade 클래스의` |
| `describe` (method) | `{methodName}() 메서드는` | `login() 메서드는` |
| `context` | `~하면`, `~이면` | `유효한 토큰이 주어지면` |
| `it` | `~한다`, `~반환한다` | `사용자 정보를 반환한다` |

---

## 3. Qualities of a Good Unit Test

Every test must satisfy all five criteria:

- **Accurate damage detection**: Tests MUST fail when code is broken. A passing test must provide confidence that the code works correctly
- **Implementation-independent**: Tests MUST still pass after refactoring internals. Test the public API behavior, not implementation details
- **Well-explained failure**: Failure messages alone must be sufficient to identify the problem
- **Readable test code**: Tests serve as documentation. Other developers must understand the intent immediately
- **Fast execution**: Unit tests must complete quickly since they are run frequently

---

## 4. Test Behaviors, Not Functions

- ❌ Do NOT mechanically create one test case per function
- ✅ Write separate test cases for each behavior a function performs
- A single function may exhibit different behaviors under different conditions — test each behavior individually
- NEVER skip error scenarios — test invalid inputs, boundary values, and exception cases alongside happy paths

---

## 5. Test One Behavior at a Time

- Testing multiple behaviors in a single test case makes failure diagnosis difficult
- ❌ Bundling multiple behaviors into one test
- ✅ Each test case verifies exactly one behavior independently
- Test case names must clearly describe the specific behavior being verified

---

## 6. Test Through Public APIs

- NEVER change private functions to public just for testing
- Test private function behavior indirectly through the public API
- Directly testing private functions couples tests to implementation — refactoring breaks tests even when behavior is unchanged
- If code is too complex to test through its public API, consider splitting it into smaller units

---

## 7. Test Double Guidelines

### Mock and Stub

- Mocks and stubs simplify tests by replacing real dependencies, but risk coupling to implementation details
- Tests using mocks/stubs may break during refactoring even when behavior is unchanged

### Fake

- Fakes are simplified implementations of real dependencies, providing more realistic tests than mocks/stubs
- Fakes decouple tests from implementation details
- Trade-off: fakes require their own maintenance

### Selection Criteria

| Situation | Recommended |
| --- | --- |
| Isolating from external systems (DB, API) | Fake or mock |
| Only need to control return values | Stub |
| Need to verify call count/args/order | Mock |
| Real dependency is lightweight and side-effect-free | Use the real dependency |

---

## 8. Shared Fixture Usage

- **State sharing (BeforeAll)**: Runs once before all test cases. Suitable for expensive dependencies, but shared mutable state between test cases can cause problems
- **Config sharing (BeforeEach)**: Runs before each test case. Guarantees isolation between test cases
- Mutable state MUST be reset via BeforeEach — sharing mutable state between test cases causes flaky tests
- Important setup values must be visible within each test case — hiding them in shared fixtures obscures test intent
- Shared constants are acceptable, but critical input values must be explicit in each test case

---

## 9. Use Appropriate Assertion Matchers

- Failure messages alone must be sufficient to diagnose the issue
- ❌ Poor assertion: failure shows only `Expected: true, But was: false` — no context
- ✅ Good assertion: failure clearly shows the difference between expected and actual values
- For collection assertions where order doesn't matter, use flexible matchers like `containsExactlyInAnyOrder`
- Leverage framework-provided matchers (e.g., AssertJ `containsAtLeast`, Jasmine `arrayContaining`)

---

## 10. Use Dependency Injection for Testability

- Hard-coded dependencies can make testing impossible
- Constructor injection allows replacing dependencies with fakes or mocks during tests
- Dependency injection improves not only testability but also modularity and flexibility
- Combine static factory methods with constructor injection to maintain both production convenience and testability

## 11. Anti-Patterns

- **테스트 없는 배포**: 테스트 커버리지 없이 프로덕션 배포하는 것은 위험. 최소한 핵심 비즈니스 로직은 테스트 필수
- **구현 세부사항 테스트**: 내부 구현에 의존하는 테스트는 리팩토링 시 깨짐. 행위(behavior) 기반 테스트 작성
- **테스트 간 의존성**: 테스트 실행 순서에 의존하면 불안정한 테스트 스위트 생성. 각 테스트는 독립적이어야 함
- **과도한 모킹**: 모든 의존성을 모킹하면 실제 동작과 괴리 발생. 통합 테스트로 보완 필요
- **매직 넘버 사용**: 테스트 데이터에 의미 없는 숫자/문자열 사용. 의도를 드러내는 상수나 팩토리 사용
- **Flaky 테스트 방치**: 간헐적으로 실패하는 테스트를 무시하면 전체 테스트 신뢰도 하락. 즉시 수정 또는 격리

## Additional References

- For integration testing patterns, see [references/integration.md](references/integration.md)
- For contract testing patterns, see [references/contract.md](references/contract.md)
- For performance testing strategies, see [references/performance.md](references/performance.md)
