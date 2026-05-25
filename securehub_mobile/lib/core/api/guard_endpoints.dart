abstract final class GuardEndpoints {
  static const String base = '/api/v1/guarding';

  static const String shifts = '$base/me/shifts/';
  static const String patrolRounds = '$base/me/patrol-rounds/';
  static const String reports = '$base/me/reports/';
  static const String postOrders = '$base/me/post-orders/';
  static const String location = '$base/me/location/';
  static const String panic = '$base/me/panic/';
  static const String dispatchTasks = '$base/me/dispatch-tasks/';
  static const String welfareChecks = '$base/me/welfare-checks/';

  static String shiftAction(String assignmentId, String action) =>
      '$base/me/shifts/$assignmentId/$action/';

  static String clock(String assignmentId) =>
      '$base/me/shifts/$assignmentId/clock/';

  static String patrolScan(String roundId) =>
      '$base/me/patrol-rounds/$roundId/scan/';

  static String patrolComplete(String roundId) =>
      '$base/me/patrol-rounds/$roundId/complete/';

  static String dispatchAction(String taskId, String action) =>
      '$base/me/dispatch-tasks/$taskId/$action/';

  static String welfareConfirm(String checkId) =>
      '$base/me/welfare-checks/$checkId/confirm/';
}
