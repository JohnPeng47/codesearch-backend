from cowboy_lib.coverage import CoverageResult, TestError, TestCoverage
from cowboy_lib.repo.repository import PatchFile
from cowboy_lib.repo.source_file import Function

from typing import Tuple, List, TYPE_CHECKING

if TYPE_CHECKING:
    from test_gen.augment_test.types import StratResult
    from cowboy_lib.test_modules import TestModule

from .eval_base import Evaluator

from src.runner.service import run_test
from src.logger import testgen_logger


class AugmentAdditiveEvaluator(Evaluator):
    """
    Iteratively evals test results and re-prompts with partially successful
    test file to **attempt** to get additive coverage
    """

    async def __call__(
        self,
        llm_results: List["StratResult"],
        tm: "TestModule",
        base_cov: TestCoverage,
        n_times: int = 1,
    ) -> Tuple[
        List[Tuple[Function, TestCoverage]],
        List[Tuple[Function, TestError]],
        List[Function],
        "TestModule",
    ]:
        """
        Main eval method, accepts a list of results from the strategy and the
        targeted test module, and a baseline coverage to compare against
        """
        test_fp = tm.test_file.path
        test_results = await self.gen_test_and_diff_coverage(
            llm_results, base_cov, test_fp, n_times
        )
        improved, failed, no_improve = await self.process_test_results(
            test_results, tm, base_cov
        )

        return improved, failed, no_improve

    # questionable decision to make non-existent func Functions ..
    async def process_test_results(
        self,
        test_results: List[Tuple[CoverageResult, str]],
        tm: "TestModule",
        base_cov: TestCoverage,
    ) -> Tuple[
        List[Tuple[Function, TestCoverage]],
        List[Tuple[Function, TestError]],
        List[Function],
    ]:
        """
        Sequentially build a set of coverage improving testcases, discarding any
        generated tests that dont contribute coverage improvements
        """
        improved_tests: List[Tuple[Function, TestCoverage]] = []
        failed_tests: List[Tuple[Function, TestError]] = []
        noimprov_tests: List[Function] = []

        for cov_res, cov_diff, test_file in test_results:
            if cov_diff:
                new_funcs = self.get_new_funcs(test_file, tm.path)
                # iterate each generated function and measure if it has coverage
                # improvement against the base
                for func in new_funcs:
                    test_error = cov_res.get_failed(func.name)
                    if test_error:
                        testgen_logger.info(f"[FAILED] Generated Func: {func.name}")
                        testgen_logger.info(f"Code: {func.to_code()}")

                        failed_tests.append((func, test_error))
                        continue

                    # TODO: make sure that this works for filename TMs as well
                    og_testfile = self.src_repo.find_file(tm.path).clone()
                    og_testfile.append(
                        func.to_code(), class_name=func.scope.name if func.scope else ""
                    )

                    patch_file = PatchFile(
                        path=str(tm.path), patch=og_testfile.to_code()
                    )
                    indvtest_cov = await run_test(
                        self.repo_name,
                        self.run_args,
                        patch_file=patch_file,
                    )

                    indv_improve = indvtest_cov.coverage - base_cov
                    if indv_improve.total_cov.covered > 0:
                        testgen_logger.info(f"[IMPROVE] Generated Func: {func.name}")
                        testgen_logger.info(f"Code: {func.to_code()}")

                        improved_tests.append((func, indv_improve))
                    else:
                        testgen_logger.info(f"[NOIMPROVE] Generated Func: {func.name}")
                        testgen_logger.info(f"Code: {func.to_code()}")

                        noimprov_tests.append((func, TestCoverage([])))

        return improved_tests, failed_tests, noimprov_tests
