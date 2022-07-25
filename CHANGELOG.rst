Changelog for stdlib_utils
==========================


0.5.2 (2022-07-25)
------------------

- Added ``is_cpu_arm``.


0.5.1 (2022-06-27)
------------------

- Removed std dev calculation from performance metrics as it takes too long.


0.5.0 (2022-06-22)
------------------

- Added more metrics to ``InfiniteLoopingParallelismMixIn``.


0.4.8 (2021-11-09)
------------------

- Updated ``TestingQueue`` so that ``len()`` and indexing raise a ``TypeError``
  like a real queue.


0.4.7 (2021-09-10)
------------------

- Updated ``configure_logging`` to only use ``stdout`` if ``path_to_log_folder`` is not given.


0.4.6 (2021-08-27)
------------------

- Added ``sort_nested_dict``.
- Updated ``configure_logging`` to allow setting custom formatters on logging handlers.


0.4.5 (2021-08-24)
------------------

- Added ``TestingQueue`` for help with tests that don't need a full multiprocessing/threading queue.


0.4.4 (2021-04-01)
------------------

- Added ``get_cms_since_init`` to ``InfiniteLoopingParallelismMixIn``.
- Fixed issue with incorrect values in performance metrics for processes running
  in Windows.


0.4.3 (2021-03-04)
------------------

- Fixed issue with ``drain_queue`` not fully draining queues in CI environments.


0.4.2 (2021-01-31)
------------------

- Added ``perform_teardown_after_loop`` kwarg to ``invoke_process_run_and_check_errors``.


0.4.0 (2021-01-28)
------------------

- Changed method name from ``unpause`` to ``resume``.
- Changed kwarg from ``timeout_secs`` to ``timeout_seconds`` to be more consistent.


0.3.11 (2020-12-31)
-------------------

- Added timeout_secs kwarg to ``safe_get`` and ``drain_queue``.


0.3.10 (2020-12-14)
-------------------

- Added pause and unpause methods to ``InfiniteLoopingParallelismMixIn``.


0.3.8 (2020-12-10)
------------------

- Added ``confirm_parallelism_is_stopped``.


0.3.7 (2020-12-08)
------------------

- Added ``confirm_queue_is_eventually_empty``.


0.3.6 (2020-11-12)
------------------

- Added ``confirm_queue_is_eventually_of_size``. Note, this is currently not supported on MacOS because MacOS does not implement ``queue.qsize()``.

- Added 50 msec delay between polling to check if queue was empty or checking ``qsize``.


0.3.5 (2020-10-23)
------------------

- Added ``is_queue_eventually_of_size``. Note, this is currently not supported on MacOS because MacOS does not implement ``queue.qsize()``.


0.3.2 (2020-10-22)
------------------

- Added kwarg for ``is_queue_eventually_empty`` and ``is_queue_eventually_empty`` for timeout.

- Added ``put_object_into_queue_and_raise_error_if_eventually_still_empty`` helper function for unit testing.


0.3.1 (2020-09-17)
------------------

- Added notebook logging format.


0.3.0 (2020-09-11)
------------------

- Added tracking of 5 longest iterations to ``InfiniteLoopingParallelismMixIn``.
