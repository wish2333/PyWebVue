# PyWebVue 2.0.0 Product Requirements Document

| Item | Detail |
|------|--------|
| Version | 2.0.0 |
| Author | wish2333 |
| Date | 2026-05-09 |
| Status | Completed |
| Based on | `issues/issues-2.0.0.md` (GPT Code Review) |

---

## 1. Background & Motivation

PyWebVue 1.x is a minimal Python + Vue desktop bridge framework (~200 lines Python core). Its design philosophy -- "clone and develop" -- has been validated by 5-8 users who successfully built desktop tools despite limited frontend experience.

A comprehensive code review (documented in `issues/issues-2.0.0.md`) identified 10 issues across security, stability, API correctness, and engineering quality dimensions. This PRD evaluates each issue against the project's actual constraints and defines the 2.0.0 scope.

### Core Constraints

1. **Minimalism is paramount** -- 200-line core is a feature, not a deficiency. 2.0.0 must not bloat the framework.
2. **Target users** -- Non-CS Python developers. API surface must stay intuitive; abstractions must justify their complexity.
3. **Backward compatibility** -- Breaking changes require strong justification. Internal APIs (`_tick`) can change; public APIs (`run_on_main_thread`, `@expose`) need migration paths.
4. **pywebview reality** -- pywebview exposes ALL methods (including `_`-prefixed) to JS. The framework cannot rely on pywebview filtering.

---

## 2. Issue Evaluation Matrix

Each issue from the code review is evaluated against three criteria:

- **Impact**: How severely does it affect users in real scenarios?
- **Alignment**: Does fixing it align with the project's minimalism philosophy?
- **Breaking**: Does it require breaking changes to the public API?

| # | Issue | Impact | Alignment | Breaking | Verdict |
|---|-------|--------|-----------|----------|---------|
| 1 | `_tick` private method called from JS | Medium | High | Yes | **Accept** -- rename to `tick`, align with pywebview conventions |
| 2 | Event name JS string injection | High | High | No | **Accept** -- framework must be safe by default |
| 3 | `@expose` leaks raw exception strings | High | High | Yes | **Accept** -- add debug/production mode |
| 4 | `call()` lacks capability boundary | Low | Low | No | **Defer** -- this is pywebview's design, document it |
| 5 | 50ms polling reentrancy | Medium | High | Yes | **Accept** -- recursive setTimeout pattern |
| 6 | `run_on_main_thread` misleading name | Medium | High | Yes | **Accept** -- rename to `run_on_bridge` |
| 7 | Debug defaults to on in dev | Low | Medium | No | **Accept** -- make opt-in |
| 8 | Version number inconsistency | Low | High | No | **Accept** -- housekeeping |
| 9 | Build config missing validation | Low | High | No | **Accept** -- fail-fast |
| 10 | `dev.py` sleep without health check | Low | Medium | No | **Accept** -- add HTTP polling |

### Deferred Items

**Issue 4 (call() capability boundary)**: pywebview's `js_api` exposes the entire Python object to JS by design. Adding a capability layer (whitelist, token validation) would significantly increase framework complexity for marginal security benefit in a desktop app context where the frontend code is local and trusted. Instead, 2.0.0 will add documentation warnings. If future use cases load remote content, this can be revisited.

---

## 3. Feature Specifications

### F1: Public `tick()` API (replaces `_tick`)

**Problem**: `_tick` is a private-named method called from JS, violating pywebview's recommended naming convention. While it works today (pywebview exposes all methods), it may break in future pywebview versions.

**Solution**:
- Rename `_tick` to `tick` as a public `@expose` method
- Update JS injection in `app.py` to call `window.pywebview.api.tick()`
- Keep `_flush_events` and `_execute_next_task` as internal methods

**Files changed**: `bridge.py`, `app.py`

**Migration**: None required -- `_tick` was documented as internal, users should not have called it directly.

---

### F2: Event Name Validation & Safe Serialization

**Problem**: `bridge.py` concatenates event names directly into JS strings:
```python
f"document.dispatchEvent(new CustomEvent('pywebvue:{event}', ..."
```
A crafted event name could break JS string structure.

**Solution**:
- Add regex validation for event names: `^[A-Za-z0-9_.:-]{1,128}$`
- Use `json.dumps` for both event name and payload
- Raise `ValueError` on invalid event names at call time (fail fast)

**Files changed**: `bridge.py`

**Migration**: Event names that contain special characters (rare in practice) will raise errors. Standard names like `progress`, `tick`, `status-update` continue to work.

---

### F3: Debug/Production Error Modes

**Problem**: `@expose` returns raw exception strings (`str(exc)`) to the frontend, potentially leaking file paths, database errors, or internal state.

**Solution**:
- Add `debug` parameter to `Bridge.__init__()` (default `False`)
- In debug mode: return `str(exc)` as before (developer convenience)
- In production mode: return generic `"Internal error"` + log full traceback server-side
- Add `error_code` field for programmatic error handling

```python
# Debug mode (default False for safety)
{"success": False, "error": "Internal error", "code": "INTERNAL_ERROR"}
# Debug mode (debug=True)
{"success": False, "error": "<full exception string>", "code": "INTERNAL_ERROR"}
```

**Files changed**: `bridge.py`

**Migration**: Users who relied on error strings for error handling should switch to `code` field. Add a deprecation note in the changelog.

---

### F4: Recursive setTimeout Tick Pattern

**Problem**: Current `setInterval` fires every 50ms regardless of whether the previous `tick()` completed. Under load, this causes concurrent reentrancy, task execution ordering issues, and CPU waste.

**Solution**: Replace `setInterval` with recursive `setTimeout` that only schedules the next tick after the previous one completes:

```javascript
(function loop() {
  window.pywebview.api.tick()
    .catch(e => console.error("pywebvue.tick error:", e))
    .finally(() => setTimeout(loop, 50));
})();
```

**Files changed**: `app.py` (JS injection string)

**Migration**: None -- internal mechanism change only.

---

### F5: Rename `run_on_main_thread` to `run_on_bridge`

**Problem**: The name `run_on_main_thread` implies execution on the GUI main thread, but the actual execution thread depends on pywebview's implementation (exposed functions may run on separate threads). This creates false expectations that could lead to subtle bugs when users rely on thread-affinity guarantees.

**Solution**:
- Rename `run_on_main_thread` to `run_on_bridge`
- Keep old name as a deprecated alias that emits a warning
- Update `register_handler` docstring to clarify thread semantics
- Remove "main thread" language from all documentation

**Files changed**: `bridge.py`, `app.py`, `CLAUDE.md`, `docs/api.md`

**Migration**:
```python
# Old (still works, emits DeprecationWarning)
api.run_on_main_thread("init_model", config)
# New
api.run_on_bridge("init_model", config)
```

---

### F6: Opt-in Debug Mode

**Problem**: `App.run()` defaults `debug=None`, which resolves to `self.dev` (True when not frozen). This means running from source always opens DevTools, which is noisy for production-style usage.

**Solution**:
- Default `debug` to `False`
- Users must explicitly pass `debug=True` when they want DevTools
- Add `debug` to `Bridge.__init__()` as well (for F3 error mode)

**Files changed**: `app.py`, `bridge.py`

**Migration**: Users who relied on automatic DevTools in dev mode need to add `debug=True` to `App.run()`.

---

### F7: Build & Dev Tooling Hardening

**Problem**: Multiple tooling gaps that cause silent failures.

**Solutions**:

**7a. Build validation**: Check `frontend_dist` exists before PyInstaller packaging. Add to `build.py`:
```python
if not Path("frontend_dist/index.html").exists():
    raise RuntimeError("frontend_dist not found. Run 'cd frontend && bun run build' first.")
```

**7b. Dev server health check**: Replace `time.sleep(2)` in `dev.py` with HTTP polling:
```python
for _ in range(40):  # 20s timeout
    try:
        urllib.request.urlopen("http://localhost:5173")
        break
    except:
        time.sleep(0.5)
else:
    raise RuntimeError("Vite dev server failed to start on port 5173")
```

**7c. Version alignment**: Set `pyproject.toml` version to `2.0.0` and create corresponding git tag.

**Files changed**: `build.py`, `dev.py`, `pyproject.toml`

---

### F8: Test Infrastructure + Core Coverage

**Problem**: Framework has zero automated tests. All verification is manual. This makes refactoring risky and regressions hard to catch.

**Solution**:
- Add `pytest` + `pytest-cov` as dev dependencies
- Create `tests/` directory with focused test modules
- Cover 5 critical areas identified by code review:

| Test Module | Coverage Target |
|-------------|----------------|
| `test_expose.py` | `expose()` decorator: success return, exception handling, debug vs prod error modes |
| `test_event.py` | `_emit()` event name validation (valid/invalid), `_flush_events()` JSON serialization safety |
| `test_task_queue.py` | `run_on_bridge()` success/timeout/unknown handler, `run_on_main_thread()` deprecated alias |
| `test_dropped_files.py` | `get_dropped_files()` buffer + clear, thread safety, `_on_drop()` parsing |
| `test_bridge_ts.py` | Frontend `bridge.ts` type correctness (compile-time, via `vue-tsc`) |

**Files added**: `tests/` directory, `pyproject.toml` (dev deps)

**Estimated effort**: 2-3 hours

---

## 4. Scope Classification

### In Scope (2.0.0)

| Feature | Priority | Complexity |
|---------|----------|------------|
| F1: Public `tick()` | P0 | Low |
| F2: Event name validation | P0 | Low |
| F3: Debug/production error modes | P0 | Medium |
| F4: Recursive setTimeout | P1 | Low |
| F5: Rename `run_on_bridge` | P1 | Medium |
| F6: Opt-in debug | P2 | Low |
| F7: Tooling hardening | P2 | Low |
| F8: Test infrastructure + core coverage | P1 | Medium |

### Out of Scope

- Issue 4: `call()` capability boundary (document-only)
- Frontend typed API generation -- future consideration
- Android/Buildozer support improvements
- New features unrelated to the code review

---

## 5. Non-Functional Requirements

### 5.1 Backward Compatibility

- `run_on_main_thread` must continue to work with a deprecation warning for at least one major version
- `_tick` can be removed outright (documented as internal)
- `@expose` return format remains `{"success": bool, "data": ..., "error": ...}`
- Frontend `call()` and `onEvent()` APIs unchanged

### 5.2 Core Size Constraint

- `bridge.py` + `app.py` combined must remain under 400 lines (current: ~270 lines)
- No new Python dependencies
- No new frontend dependencies

### 5.3 Performance

- Tick latency must not increase (target: < 1ms per tick with empty queues)
- Event validation overhead must be negligible (< 0.01ms per `_emit` call)

---

## 6. Implementation Phases

### Phase 1: Security & Stability (F1 + F2 + F4)

Core safety fixes with minimal API impact.

**Changes**:
1. Rename `_tick` to `tick` in `bridge.py`
2. Add event name regex validation + `json.dumps` for event name in `bridge.py`
3. Replace `setInterval` with recursive `setTimeout` in `app.py`

**Estimated effort**: 1-2 hours

### Phase 2: API Correctness (F3 + F5 + F6)

Public API refinements with migration paths.

**Changes**:
1. Add `debug` param to `Bridge.__init__`, modify `@expose` error handling
2. Rename `run_on_main_thread` to `run_on_bridge`, add deprecated alias
3. Change `App.run()` debug default to `False`

**Estimated effort**: 2-3 hours

### Phase 3: Tooling & Documentation (F7)

Build and dev experience improvements.

**Changes**:
1. Add `frontend_dist` validation to `build.py`
2. Replace `sleep(2)` with HTTP health check in `dev.py`
3. Bump version to `2.0.0` in `pyproject.toml`
4. Update `CLAUDE.md`, `docs/api.md`, `README.md` with new APIs

**Estimated effort**: 1-2 hours

### Phase 4: Test Infrastructure & Coverage (F8)

Automated testing foundation.

**Changes**:
1. Add `pytest`, `pytest-cov` to dev dependencies
2. Create `tests/` with 4 test modules (expose, event, task_queue, dropped_files)
3. Verify frontend types via `vue-tsc --noEmit`
4. Write testing guidance doc `docs/testing.md`

**Estimated effort**: 2-3 hours

---

## 7. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `run_on_main_thread` rename breaks downstream projects | Medium | Medium | Keep deprecated alias with warning |
| Event name validation rejects valid names | Low | Low | Regex allows common separators (`-_.:`) |
| Debug=False default confuses developers | Medium | Low | Log a hint: "Pass debug=True for detailed errors" |
| Recursive setTimeout introduces tick latency | Low | Medium | 50ms interval unchanged, only scheduling mechanism differs |

---

## 8. Acceptance Criteria

- [x] All 8 features (F1-F8) implemented and verified
- [x] `main.py` demo runs without modification (backward compatible)
- [x] Core code (`bridge.py` + `app.py`) under 400 lines (362 lines)
- [x] No new runtime Python/frontend dependencies (pytest is dev-only)
- [x] `CLAUDE.md` updated with new APIs
- [x] Test coverage >= 75% (bridge.py 96%, overall 78%)
- [x] Testing guide written (`docs/testing.md`)
- [ ] Git tag `v2.0.0` created

---

## 9. Implementation Record

**Date**: 2026-05-09
**Status**: Completed

### Files Changed

| File | Lines | Change Description |
|------|-------|--------------------|
| `pywebvue/bridge.py` | 227 (+40) | F1: `_tick` -> `tick`; F2: `_EVENT_RE` validation + `json.dumps` event name; F3: `expose` debug/production error modes + `Bridge(debug=)`; F5: `run_on_bridge` + deprecated alias |
| `pywebvue/app.py` | 135 (net 0) | F1+F4: recursive `setTimeout` calling `tick()`; F6: `debug` defaults to `False` |
| `build.py` | +6 | F7a: `frontend_dist` existence check before desktop build |
| `dev.py` | +12/-2 | F7b: HTTP health check polling `localhost:5173` (20s timeout) replaces `sleep(2)` |
| `pyproject.toml` | 1 | F7c: `version = "2.0.0"` |
| `CLAUDE.md` | ~10 | Updated: `tick()`, `run_on_bridge`, `ApiResponse` with `code` field, debug mode docs |

### New Dependencies

None.

### Core Size

`bridge.py` (227) + `app.py` (135) = **362 lines** (under 400-line constraint).

### Breaking Changes & Migration

| Change | Impact | Migration |
|--------|--------|-----------|
| `@expose` returns `"code": "INTERNAL_ERROR"` field | Additive -- existing code checking `success` unaffected | None needed |
| `@expose` hides error details by default | Error strings now return `"Internal error"` unless `Bridge(debug=True)` | Pass `debug=True` during development |
| `App.run()` no longer auto-enables DevTools | DevTools off by default | Add `debug=True` to `App.run()` when needed |
| `_tick` renamed to `tick` | Internal API, not documented for user use | None needed |
| `run_on_main_thread` deprecated | Still works, emits `DeprecationWarning` | Switch to `run_on_bridge` |

### Backward Compatibility

`main.py` demo runs without modification. All existing `@expose` methods, `call()`, `onEvent()`, `_emit()` signatures unchanged.

### Code Review Notes

Two issues flagged by automated review, resolved as follows:

1. **`args[0]` safety in `expose`** -- Fixed: added `isinstance(args[0], Bridge)` guard so the decorator degrades gracefully on non-instance calls.
2. **Adjacent f-string JS injection "broken"** -- False positive: Python's implicit string concatenation (`f"a" f"b"` = `"ab"`) produces a single concatenated string passed to `evaluate_js`. The original `setInterval` code used the same pattern and worked correctly.

### Phase 4: Test Infrastructure & Coverage (F8)

**Date**: 2026-05-09
**Status**: Completed

#### Files Added

| File | Description |
|------|-------------|
| `tests/__init__.py` | Package marker |
| `tests/test_expose.py` | 6 cases -- `@expose` success return, prod error hiding, debug error detail, path leak prevention, standalone function |
| `tests/test_event.py` | 17 cases -- valid/invalid event name validation (parametrized), queue draining, `json.dumps` serialization, window close handling, `_FakeWindow` mock helper |
| `tests/test_task_queue.py` | 8 cases -- `run_on_bridge` success/timeout/unknown handler/exception propagation, `run_on_main_thread` deprecated alias + warning, concurrent multi-thread enqueuing, `_start_tick_loop` helper |
| `tests/test_dropped_files.py` | 7 cases -- empty buffer, path parsing, missing path filtering, malformed event, buffer clear on read, concurrent drop+read thread safety |
| `docs/testing.md` | Testing guide: run commands, test structure, coverage scope, writing new tests patterns, CI integration |

#### Files Modified

| File | Change |
|------|--------|
| `pyproject.toml` | Added `pytest>=8.0`, `pytest-cov>=6.0` to `[dependency-groups].dev` |

#### Test Results

```
38 passed in 0.92s
```

#### Coverage

| Module | Stmts | Miss | Cover |
|--------|-------|------|-------|
| `pywebvue/__init__.py` | 3 | 0 | 100% |
| `pywebvue/bridge.py` | 132 | 5 | **96%** |
| `pywebvue/app.py` | 49 | 35 | 29% (expected -- requires pywebview window) |
| **TOTAL** | **184** | **40** | **78%** |

`app.py` 低覆盖率是预期行为：窗口创建、JS 注入、drag-and-drop 注册均依赖 pywebview 运行时，属于集成测试范畴。

#### Key Design Decisions

1. **不 mock pywebview** -- Bridge 的核心逻辑（事件队列、任务调度、drop 缓存）全部可脱离 pywebview 直接测试。仅 `_flush_events` 中的 `evaluate_js` 需要 `_FakeWindow` 轻量 mock。

2. **tick 循环模拟** -- 生产环境由 JS timer 驱动 `tick()`，测试中使用 `_start_tick_loop()` 辅助函数在后台线程中以 20ms 间隔调用 `_execute_next_task()`，最小化与真实行为的差异。

3. **CI 阈值 75%** -- `app.py` 的窗口依赖逻辑拉低整体覆盖率，`--cov-fail-under=75` 作为 CI 门禁值。

#### Testing Guidance

See [docs/testing.md](testing.md) for:
- 运行命令
- 测试结构说明
- 编写新测试的模式（Bridge 方法、事件推送、任务队列、拖拽文件）
- CI 集成建议
