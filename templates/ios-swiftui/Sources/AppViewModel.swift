import SwiftUI

@MainActor
final class AppViewModel: ObservableObject {
    @Published var tapCount = 0

    func incrementCounter() {
        tapCount += 1
    }
}
