"""
Session
========
"""

import functools
import grpc
import logging
from ansys import dpf
from ansys.grpc.dpf import base_pb2, session_pb2, session_pb2_grpc
from ansys.dpf.core.errors import protect_grpc
from ansys.dpf.core.common import _common_percentage_progress_bar

LOG = logging.getLogger(__name__)
LOG.setLevel('DEBUG')



class Session:
    """A class used to a user session on the server, it allows to plan events 
    call backs from the server when workflows are running.
    A session is started every time a ``'DpfServer'`` is created.
    """
    def __init__(self, server=None):
        if server is None:
            server = dpf.core._global_server()

        self._server = server

        self._stub = self._connect()
        self.__send_init_request()      
        self.add_progress_system()
        
    def _connect(self):
        """Connect to the grpc service"""
        return session_pb2_grpc.SessionServiceStub(self._server.channel)
    
    @protect_grpc
    def __send_init_request(self):
        request = session_pb2.CreateSessionRequest()
        self._message = self._stub.Create(request)
        
    def add_workflow(self,worflow, identifier):
        """Add a workflow to the session. It allows to follow the workflow's 
        events while it's running. 
        This method is automatically called when a workflow's output 
        is requested.
        
        Parameters
        ----------
        worflow : Workflow
        
        identifier : str
            name given to the workflow
        """
        request = session_pb2.AddRequest()
        request.session.CopyFrom(self._message)
        request.wf.CopyFrom(worflow._message)
        request.identifier=identifier
        self._stub.Add(request)
        
    def add_operator(self,operator, pin, identifier):
        """Add a workflow made of the input operator and all his ancestors
        to the session. It allows to follow the workflow's 
        events while it's running. 
        This method is automatically called when an operator's output 
        is requested and the opetion op.progress_bar is set to ``'True'``.
        
        Parameters
        ----------
        operator : Operator
        
        pin : int
            output pin number requested
        
        identifier : str
            name given to the workflow
        """
        request = session_pb2.AddRequest()
        request.session.CopyFrom(self._message)
        request.op_output.op.CopyFrom(operator._message)
        request.op_output.pin=pin
        request.identifier=identifier
        self._stub.Add(request)
        
    def listen_to_progress(self):
        """Starts a progress bar and update it everytime an operator is 
        finished        
        """
        service = self._stub.ListenToProgress(self._message)
        bar =_common_percentage_progress_bar("Workflow running")
        bar.start()
        for chunk in service:
            try:
                bar.update(chunk.progress.progress_percentage)
                if len(chunk.state.state):
                    LOG.warning(chunk.state.state)
            except Exception as e:
                raise e
                pass
        try:
            bar.finish()
        except :
            pass
            
    def add_progress_system(self):
        """Asks the session to start recording progress events.
        Called when the session is started.
        """
        self._stub.AddProgressEventSystem(self._message)
        
    def flush_workflows(self):
        """This removes the handle on the workflow by the session"""
        self._stub.FlushWorkflows(self._message)
        
    
    def __del__(self):
        try:
            self._stub.Delete(self._message)
        except:
            pass
        
