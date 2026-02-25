import SwiftUI

struct ContentView: View {
    @StateObject private var viewModel = AppViewModel()

    var body: some View {
        VStack(spacing: 16) {
            Text("Hello from __APP_NAME__")
                .font(.title2)

            Text("Core feature taps: \(viewModel.tapCount)")
                .font(.headline)

            Button("Tap to Increment") {
                viewModel.incrementCounter()
            }
            .buttonStyle(.borderedProminent)
        }
        .padding(24)
    }
}

#Preview {
    ContentView()
}
