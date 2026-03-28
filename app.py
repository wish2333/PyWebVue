"""Test business API class."""

from pywebvue import ApiBase, Result, ErrCode


class TestApi(ApiBase):
    def health_check(self) -> Result:
        self.logger.info("health_check called")
        self.emit("log:add", {"level": "INFO", "message": "Health check OK"})
        return Result.ok(data={"version": "0.1.0", "status": "healthy"})

    def force_error(self) -> Result:
        self.logger.error("force_error called")
        return Result.fail(ErrCode.INTERNAL_ERROR, detail="This is a test error")
