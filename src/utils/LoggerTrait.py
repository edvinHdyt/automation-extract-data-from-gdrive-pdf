import logging
import sys

class LoggerTrait:
    @property
    def logger(self) -> logging.Logger:
        if not hasattr(self, "_logger"):
            self._logger = logging.getLogger(self.__class__.__name__)
            self._logger.setLevel(logging.INFO)

            if not self._logger.handlers:
                console_handler = logging.StreamHandler(sys.stdout)

                formatter = logging.Formatter(
                    fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                    datefmt="%H:%M:%S"
                )

                console_handler.setFormatter(formatter)
                self._logger.addHandler(console_handler)

        return self._logger