import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

import '../../../core/api/api_client.dart';
import '../../../core/api/api_endpoints.dart';
import '../../../core/auth/auth_notifier.dart';

part 'messages_provider.g.dart';

class InboxMessage {
  const InboxMessage({
    required this.id,
    required this.title,
    required this.body,
    required this.messageType,
    required this.createdAt,
    this.sentAt,
  });

  final String id;
  final String title;
  final String body;
  final String messageType;
  final DateTime createdAt;
  final DateTime? sentAt;

  factory InboxMessage.fromJson(Map<String, dynamic> json) => InboxMessage(
        id: (json['id'] ?? '').toString(),
        title: (json['title'] ?? '').toString(),
        body: (json['body'] ?? '').toString(),
        messageType: (json['message_type'] as String?) ?? 'general',
        createdAt: json['created_at'] != null
            ? DateTime.tryParse(json['created_at'].toString()) ?? DateTime.now()
            : DateTime.now(),
        sentAt: json['sent_at'] != null
            ? DateTime.tryParse(json['sent_at'].toString())
            : null,
      );
}

@riverpod
Future<List<InboxMessage>> inboxMessages(Ref ref) async {
  final authState = ref.watch(authNotifierProvider);
  if (authState is! AuthAuthenticated) return [];

  final dio = ref.watch(dioProvider);
  final response = await dio.get<dynamic>(ApiEndpoints.messages);
  
  final data = response.data;
  List<dynamic> messageList = [];
  
  if (data is List) {
    messageList = data;
  } else if (data is Map<String, dynamic> && data['results'] is List) {
    messageList = data['results'] as List<dynamic>;
  }

  return messageList
      .cast<Map<String, dynamic>>()
      .map(InboxMessage.fromJson)
      .toList();
}

@riverpod
Future<void> markMessageAsRead(MarkMessageAsReadRef ref, String messageId) async {
  // The backend does not expose a mobile-facing "mark read" endpoint yet.
  // Keep this provider as a no-op so the UI remains stable until read state is
  // introduced server-side.
  return;
}
