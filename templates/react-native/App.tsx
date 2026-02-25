import { StatusBar } from "expo-status-bar";
import { useState } from "react";
import { Pressable, SafeAreaView, StyleSheet, Text, View } from "react-native";

export default function App() {
  const [count, setCount] = useState(0);

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.card}>
        <Text style={styles.title}>Hello from __APP_NAME__</Text>
        <Text style={styles.subtitle}>Core feature count: {count}</Text>
        <Pressable style={styles.button} onPress={() => setCount((value) => value + 1)}>
          <Text style={styles.buttonLabel}>Increment</Text>
        </Pressable>
      </View>
      <StatusBar style="auto" />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: "#f2f7ff",
    paddingHorizontal: 20
  },
  card: {
    width: "100%",
    maxWidth: 420,
    backgroundColor: "#ffffff",
    borderRadius: 16,
    padding: 24,
    gap: 14,
    borderWidth: 1,
    borderColor: "#d2def8"
  },
  title: {
    fontSize: 24,
    fontWeight: "700",
    color: "#1b2c4b"
  },
  subtitle: {
    fontSize: 18,
    color: "#2e4f80"
  },
  button: {
    backgroundColor: "#2f6ce4",
    borderRadius: 999,
    paddingVertical: 12,
    alignItems: "center"
  },
  buttonLabel: {
    color: "#fff",
    fontWeight: "600"
  }
});
