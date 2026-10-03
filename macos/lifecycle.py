"""Serialized audio lifecycle. Adapters do I/O; this module is hardware independent."""
import threading
import time


class AudioLifecycle:
    def __init__(self, audio, reset_input, status, clock=time.monotonic, prepare_input=None):
        self.audio = audio
        self.reset_input = reset_input
        self.prepare_input = prepare_input or (lambda: None)
        self.status = status
        self.clock = clock
        self.lock = threading.RLock()
        self.state = 'suspended'
        self.desired = False
        self.generation = 0
        self.epoch = 0
        self.last_callback = None
        self.started = None
        self.retry_at = 0
        self.error = None
        self.fn_released = False

    def _state(self, state):
        if self.state != state:
            self.state = state
            self.status(state)

    def suspend(self, reason='sleep'):
        with self.lock:
            if self.state == 'shutting-down':
                return
            if self.desired or self.state != 'suspended':
                self.epoch += 1
                self.generation += 1
            self.desired = False
            self.fn_released = False
            self._state('suspended')
            self.reset_input()
            self._close()

    def _close(self):
        self.last_callback = None
        self.started = None
        try:
            self.audio.close()
        except Exception as exc:
            self.error = str(exc)
            self.status('audio cleanup failed: ' + self.error)
            return False
        self.last_callback = None
        self.started = None
        return True

    def resume(self):
        with self.lock:
            if self.state == 'shutting-down' or self.desired:
                return
            self.desired = True
            self.retry_at = 0
            self._recover()

    def _recover(self):
        self.generation += 1
        self.epoch += 1
        self.fn_released = False
        self.reset_input()
        self._state('recovering')
        if not self._close():
            self.retry_at = self.clock() + 2.0
            return
        self.started = self.clock()
        self.retry_at = self.started + 2.0
        generation = self.generation
        try:
            self.prepare_input()
            self.audio.open(generation)
            self.error = None
        except Exception as exc:
            self.error = str(exc)
            self._close()
            self.status('input recovery failed: ' + self.error)

    def callback(self, generation, consume=None):
        # Never block a realtime audio callback behind engine.stop()/removeTap.
        if not self.lock.acquire(blocking=False):
            return False
        try:
            if not self.desired or generation != self.generation:
                return False
            self.last_callback = self.clock()
            if self.state == 'recording' and consume:
                consume()
            return True
        finally:
            self.lock.release()

    def tick(self):
        with self.lock:
            if not self.desired or self.state == 'shutting-down':
                return
            now = self.clock()
            try:
                running = self.audio.running()
            except Exception:
                running = False
            heartbeat = self.last_callback
            if running and heartbeat is not None and now - heartbeat <= 2.0:
                if self.state == 'recovering':
                    self._state('ready')
                return
            if now >= self.retry_at and (not running or heartbeat is None or now - heartbeat > 2.0):
                self._recover()

    def press(self):
        with self.lock:
            if self.state != 'ready' or not self.fn_released:
                return False
            self._state('recording')
            return True

    def release(self):
        with self.lock:
            self.fn_released = True
            if self.state != 'recording':
                return False
            self._state('ready')
            return True

    def can_deliver(self, epoch):
        return self.desired and self.state in ('ready', 'recording') and epoch == self.epoch

    def shutdown(self):
        with self.lock:
            self.desired = False
            self.generation += 1
            self.epoch += 1
            self._state('shutting-down')
            self.reset_input()
            self._close()
