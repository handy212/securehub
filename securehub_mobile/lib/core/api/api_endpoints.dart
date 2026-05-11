abstract final class ApiEndpoints {
  static const String login = '/api/v1/auth/login/';
  static const String refresh = '/api/v1/auth/refresh/';
  static const String googleLogin = '/api/v1/auth/google/';
  static const String logout = '/api/v1/auth/logout/';
  static const String passwordReset = '/api/v1/auth/password-reset/';
  static const String profile = '/api/v1/profile/';
  static const String sites = '/api/v1/sites/';
  static const String alarmDevices = '/api/v1/alarm-devices/';
  static const String subsystems = '/api/v1/subsystems/';
  static const String zones = '/api/v1/zones/';
  static const String cctvChannels = '/api/v1/cctv/channels/';
  static const String registerDevice = '/api/v1/notifications/register-device/';
  static const String messages = '/api/v1/communication/messages/';
  static const String emergencyStatus = '/api/v1/emergency/status/';
  static const String emergencyRequests = '/api/v1/emergency/requests/';

  static String siteDetail(String siteId) => '/api/v1/sites/$siteId/';
  static String sitePoll(String siteId) => '/api/v1/sites/$siteId/poll/';
  static String siteStatus(String siteId) => '/api/v1/sites/$siteId/status/';
  static String siteEvents(String siteId) => '/api/v1/sites/$siteId/events/';
  static String siteCommands(String siteId) =>
      '/api/v1/sites/$siteId/commands/';
  static String eventPicture(String siteId, String eventId) =>
      '/api/v1/alarms/sites/$siteId/events/$eventId/picture/';
  static String subsystemCommand(
    String siteId,
    String subsystemId,
    String action,
  ) => '/api/v1/sites/$siteId/subsystems/$subsystemId/$action/';
  static String cameraLive(String siteId, String channelId) =>
      '/api/v1/sites/$siteId/cameras/$channelId/live/';
  static String cameraPtz(String siteId, String channelId, String action) =>
      '/api/v1/sites/$siteId/cameras/$channelId/ptz/$action/';
  static String emergencyLocation(String requestId) =>
      '/api/v1/emergency/requests/$requestId/location/';
  static String emergencyCancel(String requestId) =>
      '/api/v1/emergency/requests/$requestId/cancel/';
}
