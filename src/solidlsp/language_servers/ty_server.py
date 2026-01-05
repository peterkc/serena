"""
Provides Python type checking via the Ty language server.
"""

import logging
import os
import pathlib
from typing import cast

from overrides import override

from solidlsp.ls import SolidLanguageServer
from solidlsp.ls_config import LanguageServerConfig
from solidlsp.lsp_protocol_handler.lsp_types import InitializeParams
from solidlsp.lsp_protocol_handler.server import ProcessLaunchInfo
from solidlsp.settings import SolidLSPSettings

log = logging.getLogger(__name__)


class TyServer(SolidLanguageServer):
    """
    Ty language server for Python type checking.
    Uses the 'ty server' command from the ty type checker (experimental).
    """

    def __init__(self, config: LanguageServerConfig, repository_root_path: str, solidlsp_settings: SolidLSPSettings):
        """
        Creates a TyServer instance. This class is not meant to be instantiated directly. Use LanguageServer.create() instead.
        """
        super().__init__(
            config,
            repository_root_path,
            ProcessLaunchInfo(cmd="ty server", cwd=repository_root_path),
            "python",
            solidlsp_settings,
        )

    @override
    def is_ignored_dirname(self, dirname: str) -> bool:
        return super().is_ignored_dirname(dirname) or dirname in ["venv", "__pycache__"]

    @staticmethod
    def _get_initialize_params(repository_absolute_path: str) -> InitializeParams:
        """
        Returns the initialize params for the Ty Language Server.
        """
        root_uri = pathlib.Path(repository_absolute_path).as_uri()
        initialize_params = {
            "processId": os.getpid(),
            "clientInfo": {"name": "Serena", "version": "0.1.0"},
            "rootPath": repository_absolute_path,
            "rootUri": root_uri,
            "capabilities": {
                "workspace": {
                    "workspaceEdit": {"documentChanges": True},
                    "didChangeConfiguration": {"dynamicRegistration": True},
                    "didChangeWatchedFiles": {"dynamicRegistration": True},
                    "symbol": {
                        "dynamicRegistration": True,
                        "symbolKind": {"valueSet": list(range(1, 27))},
                    },
                },
                "textDocument": {
                    "synchronization": {
                        "dynamicRegistration": True,
                        "willSave": True,
                        "willSaveWaitUntil": True,
                        "didSave": True,
                    },
                    "hover": {"dynamicRegistration": True, "contentFormat": ["markdown", "plaintext"]},
                    "definition": {"dynamicRegistration": True},
                    "references": {"dynamicRegistration": True},
                    "documentSymbol": {
                        "dynamicRegistration": True,
                        "symbolKind": {"valueSet": list(range(1, 27))},
                        "hierarchicalDocumentSymbolSupport": True,
                    },
                    "publishDiagnostics": {"relatedInformation": True},
                },
            },
            "workspaceFolders": [
                {
                    "uri": root_uri,
                    "name": os.path.basename(repository_absolute_path),
                }
            ],
        }
        return cast(InitializeParams, initialize_params)

    def _start_server(self) -> None:
        """
        Starts the Ty Language Server.
        """

        def do_nothing(params: dict) -> None:
            return

        def window_log_message(msg: dict) -> None:
            log.info(f"Ty LSP: window/logMessage: {msg}")

        def check_experimental_status(params: dict) -> None:
            if params.get("quiescent") == True:
                self.completions_available.set()

        # Set up notification handlers
        self.server.on_request("client/registerCapability", do_nothing)
        self.server.on_notification("window/logMessage", window_log_message)
        self.server.on_notification("$/progress", do_nothing)
        self.server.on_notification("textDocument/publishDiagnostics", do_nothing)
        self.server.on_notification("experimental/serverStatus", check_experimental_status)

        log.info("Starting ty server process")
        self.server.start()

        initialize_params = self._get_initialize_params(self.repository_root_path)

        log.info("Sending initialize request from LSP client to ty server and awaiting response")
        init_response = self.server.send.initialize(initialize_params)
        log.info(f"Received initialize response from ty server: {init_response}")

        self.server.notify.initialized({})
