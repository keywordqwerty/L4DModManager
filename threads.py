import threading
import traceback

class TaskWorker(threading.Thread):
    def __init__(self, task_function, on_finish=None, log_callback=None, *args, **kwargs):
        super().__init__(daemon=True)
        self.task_function = task_function
        self.on_finish = on_finish
        self.log_callback = log_callback
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            # Execute the passed task function with its arguments
            self.task_function(self.log_callback, *self.args, **self.kwargs)
        except Exception as error:
            # Capture any unhandled crash and send it to the UI log
            if self.log_callback:
                self.log_callback(f"[Worker Error] An unexpected error occurred: {error}")
        finally:
            # Always notify the UI that the work is finished, even if it failed
            if self.on_finish:
                self.on_finish()