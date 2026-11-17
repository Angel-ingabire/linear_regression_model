import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:african_enrollment_app/main.dart';

void main() {
  // Launch the EnrollmentIQ application.
  Future<void> launchApp(WidgetTester tester) async {
    await tester.pumpWidget(const EnrollmentApp());
    await tester.pumpAndSettle();
  }

  // Select an option from a dropdown.
  Future<void> selectDropdown(
    WidgetTester tester,
    int index,
    String option,
  ) async {
    final dropdown = find.byType(DropdownButtonFormField<String>).at(index);

    await tester.ensureVisible(dropdown);
    await tester.pumpAndSettle();

    await tester.tap(dropdown);
    await tester.pumpAndSettle();

    // Search within the opened dropdown menu.
    final optionFinder = find.text(option);

    if (optionFinder.evaluate().isEmpty) {
      // Some dropdown items are built only when scrolled into view.
      final menuScrollable = find
          .ancestor(
            of: find.byType(DropdownMenuItem<String>).first,
            matching: find.byType(Scrollable),
          )
          .first;

      await tester.scrollUntilVisible(
        optionFinder,
        150,
        scrollable: menuScrollable,
        maxScrolls: 50,
      );

      await tester.pumpAndSettle();
    }

    expect(optionFinder, findsWidgets);

    await tester.tap(optionFinder.last);
    await tester.pumpAndSettle();
  }

  // TEST 1: Verify the application loads.
  testWidgets('EnrollmentIQ screen loads successfully', (
    WidgetTester tester,
  ) async {
    await launchApp(tester);

    expect(find.text('EnrollmentIQ'), findsOneWidget);
    expect(find.byType(Scaffold), findsOneWidget);
    expect(find.text('Country Details'), findsOneWidget);
    expect(find.text('1 / 4'), findsOneWidget);
    expect(find.text('Continue'), findsOneWidget);
  });

  // TEST 2: Verify country-related input fields.
  testWidgets('Country fields are displayed', (WidgetTester tester) async {
    await launchApp(tester);

    expect(find.text('Country'), findsOneWidget);
    expect(find.text('Geographic Region'), findsOneWidget);
    expect(find.text('Income Classification'), findsOneWidget);
  });

  // TEST 3: Verify required field validation.
  testWidgets('Cannot continue without country details', (
    WidgetTester tester,
  ) async {
    await launchApp(tester);

    await tester.tap(find.text('Continue'));
    await tester.pumpAndSettle();

    expect(find.text('Country Details'), findsOneWidget);
    expect(find.text('Please select Country'), findsOneWidget);
    expect(find.text('1 / 4'), findsOneWidget);
  });

  // TEST 4: Verify navigation from Step 1 to Step 2.
  testWidgets('Can navigate from country details to demographics', (
    WidgetTester tester,
  ) async {
    await launchApp(tester);

    // Select the first country to avoid unnecessary menu scrolling.
    await selectDropdown(tester, 0, 'AGO');

    // Select the region.
    await selectDropdown(tester, 1, 'Sub-Saharan Africa');

    // Select the income group.
    await selectDropdown(tester, 2, 'Low income');

    // Move to the next step.
    await tester.tap(find.text('Continue'));
    await tester.pumpAndSettle();

    expect(find.text('Demographics'), findsOneWidget);
    expect(find.text('2 / 4'), findsOneWidget);
    expect(find.text('Observation Year'), findsOneWidget);
    expect(find.text('Back'), findsOneWidget);
  });

  // TEST 5: Verify Back is hidden on the first step.
  testWidgets('Back button is hidden on first step', (
    WidgetTester tester,
  ) async {
    await launchApp(tester);

    expect(find.text('Back'), findsNothing);
    expect(find.text('Continue'), findsOneWidget);
  });

  // TEST 6: Verify the screen contains a scrollable ListView.
  testWidgets('Form uses a scrollable ListView', (WidgetTester tester) async {
    await launchApp(tester);

    expect(find.byType(ListView), findsOneWidget);
    expect(find.byType(Scrollbar), findsOneWidget);
  });

  // TEST 7: Verify the form supports scrolling.
  testWidgets('User can scroll the form', (WidgetTester tester) async {
    await launchApp(tester);

    final listFinder = find.byType(ListView);

    expect(listFinder, findsOneWidget);

    await tester.drag(listFinder, const Offset(0, -300));

    await tester.pumpAndSettle();

    // Verify that the app remains functional after scrolling.
    expect(find.byType(ListView), findsOneWidget);
    expect(find.text('EnrollmentIQ'), findsOneWidget);
    expect(find.text('Continue'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
