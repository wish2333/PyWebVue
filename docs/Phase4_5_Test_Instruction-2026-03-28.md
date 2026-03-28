# Phase 4 & 5 Test Instructions

Date: 2026-03-28

---

## Phase 4 Tests

### 4.1 ProcessManager - Timeout + Reset

#### Test 1: Import check
```bash
uv run python -c "from pywebvue import ProcessManager, ProcessState; print('OK')"
```
Expected: prints `OK` with no errors.

#### Test 2: Timeout auto-stop
Create a test script `test_timeout.py`:
```python
import time
import threading
from pywebvue import ApiBase, ProcessManager, ProcessState, Result

class MockApi(ApiBase):
    pass

api = MockApi()
pm = ProcessManager(api, name="test")

# Start a long-running process with a 3-second timeout
result = pm.start(
    cmd=["python", "-c", "import time; time.sleep(30)"],
    timeout=3,
)
assert result.is_ok, f"Start failed: {result.msg}"
print(f"State: {pm.state.value}")
assert pm.state == ProcessState.RUNNING

# Wait for timeout to trigger
time.sleep(5)
print(f"State after timeout: {pm.state.value}")
assert pm.state == ProcessState.STOPPED, "Process should be stopped after timeout"
print("PASS: timeout auto-stop works")
```
```bash
uv run python test_timeout.py
```
Expected: prints `PASS: timeout auto-stop works`.

#### Test 3: Reset and restart
Create a test script `test_reset.py`:
```python
from pywebvue import ApiBase, ProcessManager, ProcessState, Result

class MockApi(ApiBase):
    pass

api = MockApi()
pm = ProcessManager(api, name="test")

# Start and stop
r1 = pm.start(cmd=["python", "-c", "print('hello')"])
assert r1.is_ok
import time; time.sleep(1)
assert pm.state in (ProcessState.STOPPED, ProcessState.RUNNING)

r2 = pm.stop()
if r2.is_ok:
    print(f"State after stop: {pm.state.value}")
    assert pm.state == ProcessState.STOPPED
    r3 = pm.reset()
    assert r3.is_ok, f"Reset failed: {r3.msg}"
    print(f"State after reset: {pm.state.value}")
    assert pm.state == ProcessState.IDLE

    # Start again
    r4 = pm.start(cmd=["python", "-c", "print('world')"])
    assert r4.is_ok, f"Restart failed: {r4.msg}"
    print("PASS: reset + restart works")
else:
    # Already stopped (process completed before stop)
    assert pm.state == ProcessState.STOPPED
    # Auto-reset should work
    r5 = pm.start(cmd=["python", "-c", "print('auto-reset')"])
    assert r5.is_ok, f"Auto-reset restart failed: {r5.msg}"
    print("PASS: auto-reset from STOPPED works")
```
```bash
uv run python test_reset.py
```
Expected: prints `PASS`.

#### Test 4: Cancel timeout on manual stop
```python
import time
from pywebvue import ApiBase, ProcessManager, ProcessState

class MockApi(ApiBase):
    pass

api = MockApi()
pm = ProcessManager(api, name="test")
pm.start(cmd=["python", "-c", "import time; time.sleep(30)"], timeout=10)
assert pm.state == ProcessState.RUNNING
print(f"Timeout remaining: {pm.timeout_remaining}s")
assert pm.timeout_remaining is not None

time.sleep(2)
pm.stop()
assert pm.state == ProcessState.STOPPED
assert pm.timeout_remaining is None, "Timeout should be cancelled after stop"
print("PASS: timeout cancelled on manual stop")
```
```bash
uv run python test_cancel_timeout.py
```

### 4.2 Build CLI Enhancements

#### Test 5: --clean flag
```bash
pywebvue create test_build --force --title "Build Test"
cd test_build
# Create dummy build/dist dirs
mkdir build dist
echo "test" > build/dummy.txt
echo "test" > dist/dummy.txt
ls build/ dist/
# Run build with --clean
uv run pywebvue build --clean --skip-frontend
# Verify build/dist were cleaned before build
```
Expected: dummy.txt files removed, build proceeds.

#### Test 6: --icon flag
```bash
cd test_build
uv run pywebvue build --skip-frontend --icon nonexistent.ico 2>&1
```
Expected: error message about icon file not found.

#### Test 7: --output-dir flag
```bash
cd test_build
uv run pywebvue build --skip-frontend --output-dir ./custom_output
ls custom_output/
```
Expected: `custom_output/dist/` and `custom_output/build/` directories exist.

### 4.3 Frontend Template Polish

#### Test 8: Toast watch source
Open `src/pywebvue/templates/project/frontend/src/components/Toast.vue.tpl` and verify:
- Line 17: `watch(() => props.items,` (not `props.items.length`)

#### Test 9: App.vue removeToast provide
Open `src/pywebvue/templates/project/frontend/src/App.vue.tpl` and verify:
- `removeToast` is provided via `provide("removeToast", removeToast)`

---

## Phase 5 Tests

### 5.1 file-tool Example

#### Test 10: Dependencies install
```bash
cd examples/file-tool
uv sync
cd frontend && bun install && cd ../..
```
Expected: all dependencies install successfully.

#### Test 11: Frontend build
```bash
cd examples/file-tool/frontend
bun run build
```
Expected: `../dist/` created with built assets.

#### Test 12: Run application
```bash
cd examples/file-tool
uv run python main.py
```
Expected:
- Window opens with dark theme
- Title bar shows "File Tool"
- FileDrop area visible
- LogPanel at bottom

#### Test 13: File drop and info
1. Drag a file onto the window
2. Expected:
   - Toast notification "File received: {path}"
   - File appears in FileDrop list
   - FileInfoCard shows metadata (name, extension, size, modified, type)
   - Log entry appears in LogPanel

#### Test 14: Process file
1. After dropping a file, click "Process File"
2. Expected:
   - Progress bar updates from 0% to 100%
   - Log entries show step progress
   - Toast "Processing complete: {name}" on completion

### 5.2 process-tool Example

#### Test 15: Dependencies install
```bash
cd examples/process-tool
uv sync
cd frontend && bun install && cd ../..
```
Expected: all dependencies install successfully.

#### Test 16: Frontend build
```bash
cd examples/process-tool/frontend
bun run build
```
Expected: `../dist/` created with built assets.

#### Test 17: Run application
```bash
cd examples/process-tool
uv run python main.py
```
Expected:
- Window opens with light theme
- Title bar shows "Process Tool"
- Command textarea with default command
- Start/Pause/Resume/Stop/Reset buttons
- StatusBadge shows "Idle"
- PID badge is hidden
- Timeout badge shows "Timeout: 30s"

#### Test 18: Start process
1. Click "Start"
2. Expected:
   - StatusBadge changes to "Running"
   - PID badge appears
   - Timeout countdown visible
   - Log entries show output lines
   - Start button becomes disabled

#### Test 19: Pause/Resume
1. While process is running, click "Pause"
2. Expected: StatusBadge shows "Paused", Pause disabled, Resume enabled
3. Click "Resume"
4. Expected: StatusBadge shows "Running"

#### Test 20: Stop and Reset
1. Click "Stop"
2. Expected: StatusBadge shows "Done"
3. Click "Reset"
4. Expected: StatusBadge shows "Idle", PID badge hidden

#### Test 21: Timeout
1. Enter a long-running command like `python -c "import time; time.sleep(60)"`
2. Click "Start"
3. Wait for timeout (config has default_timeout: 30)
4. Expected:
   - Warning toast "Process timed out after 30s"
   - StatusBadge shows "Done"
   - Process is stopped

### 5.3 User Guide

#### Test 22: Review completeness
Open `docs/user-guide.md` and verify all 10 sections are present:
1. Quick Start
2. Project Structure
3. Adding Business API Methods
4. Frontend-Backend Communication
5. Custom Error Codes
6. Subprocess Management (ProcessManager)
7. Configuration Reference (config.yaml)
8. Development Mode (Vite HMR)
9. Packaging & Distribution
10. Pre-built Components

---

## Cleanup

```bash
# Remove test artifacts
rm -rf test_build test_timeout.py test_reset.py test_cancel_timeout.py
```
