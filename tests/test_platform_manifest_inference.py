import unittest

from tools.project_tools import parse_platform_manifest


class PlatformManifestInferenceTests(unittest.TestCase):
    def test_infers_nextjs_from_freeform_text(self):
        manifest = """
        Recommended stack:
        - Frontend: Next.js with TypeScript
        - Backend: Express
        Notes: A Python CLI exporter could be added later.
        """
        parsed = parse_platform_manifest(manifest)
        self.assertEqual(parsed["template"], "nextjs")
        self.assertEqual(parsed["selected_platform"], "nextjs")

    def test_infers_ios_swiftui_from_freeform_text(self):
        manifest = """
        The app should be built as a native iOS SwiftUI experience.
        Suggested project stack: SwiftUI + Combine.
        """
        parsed = parse_platform_manifest(manifest)
        self.assertEqual(parsed["template"], "ios-swiftui")
        self.assertEqual(parsed["selected_platform"], "ios-swiftui")


if __name__ == "__main__":
    unittest.main()
