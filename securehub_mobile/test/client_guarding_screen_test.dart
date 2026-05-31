import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:securehub_mobile/core/theme/app_theme.dart';
import 'package:securehub_mobile/features/client_guarding/models/client_guarding_models.dart';
import 'package:securehub_mobile/features/client_guarding/providers/client_guarding_provider.dart';
import 'package:securehub_mobile/features/client_guarding/screens/client_guarding_screen.dart';

void main() {
  testWidgets('client guarding screen shows safe portal data', (tester) async {
    const snapshot = ClientGuardingSnapshot(
      counts: ClientGuardingCounts(
        sites: 1,
        reports: 1,
        patrols: 1,
        assignments: 1,
        guards: 1,
      ),
      access: [
        ClientGuardingAccess(
          siteId: 'site-1',
          siteName: 'Warehouse North',
          role: 'manager',
          canViewReports: true,
          canViewPatrols: true,
          canViewAttendance: true,
          canViewGuards: true,
        ),
      ],
      reports: [
        ClientGuardingReport(
          id: 'report-1',
          title: 'Daily activity report',
          reportType: 'Daily activity',
          body: 'All patrols completed.',
          siteName: 'Warehouse North',
          postName: 'Main Gate',
          guardName: 'Ama Mensah',
        ),
      ],
      patrolRounds: [
        ClientGuardingPatrolRound(
          id: 'patrol-1',
          routeName: 'Perimeter',
          siteName: 'Warehouse North',
          postName: 'Main Gate',
          guardName: 'Ama Mensah',
          status: 'Scheduled',
          scanCount: 2,
        ),
      ],
      assignments: [
        ClientGuardingAssignment(
          id: 'assignment-1',
          guardName: 'Ama Mensah',
          siteName: 'Warehouse North',
          postName: 'Main Gate',
          status: 'Assigned',
        ),
      ],
      knownGuards: [
        ClientKnownGuard(
          assignmentId: 'assignment-1',
          guardName: 'Ama Mensah',
          employeeNumber: 'G-DEMO-001',
          guardStatus: 'Active',
          siteName: 'Warehouse North',
          postName: 'Main Gate',
          assignmentStatus: 'Assigned',
          verifiedCredentials: ['Security License'],
        ),
      ],
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          clientGuardingSnapshotProvider.overrideWith((ref) async => snapshot),
        ],
        child: MaterialApp(
          theme: AppTheme.light,
          home: const ClientGuardingScreen(),
        ),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    expect(find.text('Know your guard'), findsOneWidget);
    expect(find.text('Ama Mensah'), findsWidgets);
    expect(find.text('G-DEMO-001 · Active'), findsOneWidget);
    expect(find.text('Security License'), findsOneWidget);
    expect(find.text('Daily activity report'), findsOneWidget);
    expect(find.textContaining('+233'), findsNothing);
  });
}
