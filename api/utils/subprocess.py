import asyncio
#from . import logger
from . import exceptions

import subprocess

def sync_run(command):
    subprocess.call(command, shell = True)

async def run(command):
    cmd = Command(command)

    await cmd._init()

    return cmd

class Command:
    def __init__(self, command):
        self.command = command
        
        self.process = None
        self.task = None

    async def _init(self):
        self.process = await asyncio.create_subprocess_shell(
            self.command,
            stdin = asyncio.subprocess.PIPE,
            stdout = asyncio.subprocess.PIPE,
            stderr = asyncio.subprocess.STDOUT
        )

        asyncio.get_event_loop().create_task(self.handle_stdout())

        await self.process.wait()

        if str(self.process.returncode) != "0":
            logger.log("error", f"Subprocess call for '{self.command}' returned non-zero exit code: {self.process.returncode}")
            raise exceptions.SubprocessError()

    async def kill(self):
        self.process.terminate()
    
    async def handle_stdout(self):
        done = False
        while not self.process.returncode and not done:
            # Process is still running
            try:
                msg = await self.process.stdout.readuntil(b"\n")
                data = msg.decode("ascii").rstrip()

                # We will eventually log this
                print(data)

            except asyncio.IncompleteReadError:
                done = True
                #logger.log("warn", "Subprocess exited while reading.")

            except asyncio.LimitOverrunError:
                # Shouldn't happen yet.
                logger.log("warn", "Subprocess limit overrun. Can't read data.")

            except:
                logger.log("error", "Failed to read data from subprocess.")