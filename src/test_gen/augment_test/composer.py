from .base_strat import BaseStrategy, TestCaseInput
from .types import StratResult
from .evaluators import (
    Evaluator,
    AugmentAdditiveEvaluator,
    AugmentParallelEvaluator,
    EvaluatorType,
    AUGMENT_EVALS,
)

from cowboy_lib.llm.invoke_llm import invoke_llm_async
from cowboy_lib.llm.models import OpenAIModel, ModelArguments
from cowboy_lib.repo.source_repo import SourceRepo
from cowboy_lib.repo.source_file import Function, LintException
from cowboy_lib.coverage import TestCoverage, TestError

from src.test_gen.augment_test.strats import AugmentStratType, AUGMENT_STRATS
from src.runner.service import RunServiceArgs
from src.exceptions import CowboyRunTimeException
from src.logger import testgen_logger


from src.config import LLM_RETRIES

from typing import Tuple, List


class Composer:
    """
    Used to instantiate different combinations of strategies for generating test cases
    """

    def __init__(
        self,
        repo_name: str,
        strat: AugmentStratType,
        evaluator: EvaluatorType,
        src_repo: SourceRepo,
        test_input: TestCaseInput,
        run_args: RunServiceArgs,
        base_cov: TestCoverage,
        api_key: str,
        verify: bool = False,
    ):
        self.repo_name = repo_name
        self.src_repo = src_repo
        self.test_input = test_input
        self.verify = verify
        self.base_cov = base_cov
        self.run_args = run_args

        self.strat: BaseStrategy = AUGMENT_STRATS[strat](self.src_repo, self.test_input)
        self.evaluator: Evaluator = AUGMENT_EVALS[evaluator](
            self.repo_name, self.src_repo, self.run_args
        )

        model_name = "gpt4"
        self.model = OpenAIModel(ModelArguments(model_name=model_name, api_key=api_key))

    def get_strat_name(self) -> str:
        return self.__class__.__name__

    def filter_overlap_improvements(
        self, tests: List[Tuple[Function, TestCoverage]]
    ) -> List[Tuple[Function, TestCoverage]]:
        no_overlap = []
        overlap_cov = self.base_cov
        for test, cov in tests:
            new_cov = overlap_cov + cov
            if new_cov.total_cov.covered > overlap_cov.total_cov.covered:
                no_overlap.append((test, cov))
                overlap_cov = new_cov

        return no_overlap

    # TODO: this function name is a lie, we should parallelize this
    async def gen_test_parallel(self, n_times: int) -> Tuple[
        List[Tuple[Function, TestCoverage]],
        List[Tuple[Function, TestError]],
        List[Function],
    ]:

        improved_tests = []
        failed_tests = []
        no_improve_tests = []

        # TODO: here is whee we initialize the StartCodeTx
        prompt = self.strat.build_prompt()
        print(f"Prompt: {prompt}")

        model_res = await invoke_llm_async(prompt, self.model, n_times)

        llm_results = [self.strat.parse_llm_res(res) for res in model_res]
        test_results = [StratResult(res, self.test_input.path) for res in llm_results]

        improved, failed, no_improve = await self.evaluator(
            test_results,
            self.test_input,
            self.base_cov,
            n_times=n_times,
        )

        improved_tests.extend(improved)
        filtered_improved = self.filter_overlap_improvements(improved_tests)
        improved_tests = filtered_improved

        failed_tests.extend(failed)
        no_improve_tests.extend(no_improve)

        return improved_tests, failed_tests, no_improve_tests

    async def gen_test_serial_additive(self, n_times: int) -> Tuple[
        List[Tuple[Function, TestCoverage]],
        List[Tuple[Function, TestError]],
        List[Function],
    ]:
        if not isinstance(self.evaluator, AugmentAdditiveEvaluator):
            raise Exception(
                f"Expected AugmentAdditiveEvaluator, got {self.evaluator.__class__}"
            )

        improved_tests = []
        failed_tests = []
        no_improve_tests = []
        prompt = self.strat.build_prompt()

        print("Prompt: ", prompt)

        for _ in range(n_times):
            retries = LLM_RETRIES
            src_file = None
            while retries > 0 and not src_file:
                try:
                    llm_res = await invoke_llm_async(
                        prompt,
                        model=self.model,
                        n_times=1,
                    )
                    src_file = self.strat.parse_llm_res(llm_res[0])
                except (SyntaxError, ValueError, LintException):
                    testgen_logger.info(f"LLM syntax error ... {retries} left")
                    retries -= 1
                    continue

            if not src_file:
                raise CowboyRunTimeException(
                    f"LLM generation failed for {self.test_input}"
                )

            test_result = [StratResult(src_file, self.test_input.path)]
            improved, failed, no_improve = await self.evaluator(
                test_result,
                self.test_input,
                self.base_cov,
                n_times=n_times,
            )
            improved_tests.extend(improved)
            filtered_improved = self.filter_overlap_improvements(improved_tests)
            improved_tests = filtered_improved

            # update test input with new functions that improved coverage
            for new_func in [
                func
                for func, _ in improved
                if func in [f[0] for f in filtered_improved]
            ]:
                self.test_input.test_file.append(
                    new_func.to_code(),
                    # wrong too, we need to check the
                    class_name=new_func.scope.name if new_func.scope else "",
                )

            failed_tests.extend(failed)
            no_improve_tests.extend(no_improve)

        return improved_tests, failed_tests, no_improve_tests

    async def generate_test(self, n_times: int) -> Tuple[
        List[Tuple[Function, TestCoverage]],
        List[Tuple[Function, TestError]],
        List[Function],
    ]:
        if isinstance(self.evaluator, AugmentAdditiveEvaluator):
            return await self.gen_test_serial_additive(n_times)
        elif isinstance(self.evaluator, AugmentParallelEvaluator):
            return await self.gen_test_parallel(n_times)
