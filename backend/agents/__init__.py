"""
科研多Agent系统 - 各类Agent实现
"""
from .main_agent import MainAgent
from .verification_agent import VerificationAgent
from .critique_agent import CritiqueAgent
from .report_agent import ReportAgent
from .experiment_design_agent import ExperimentDesignAgent
from .evaluation_agent import EvaluationAgent
from .information_agent import InformationAgent
from .modeling_agent import ModelingAgent

__all__ = [
    "MainAgent",
    "VerificationAgent", 
    "CritiqueAgent",
    "ReportAgent",
    "ExperimentDesignAgent",
    "EvaluationAgent",
    "InformationAgent",
    "ModelingAgent"
] 