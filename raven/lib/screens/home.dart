import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:sensors_plus/sensors_plus.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

import 'map_saver.dart';

class Home extends StatefulWidget {
  const Home({super.key});

  @override
  State<Home> createState() => _HomeState();
}

class _HomeState extends State<Home> {
  Map<String, double> imuData = {
    "accel_x": 0.0,
    "accel_y": 0.0,
    "accel_z": 0.0,
    "gyro_x": 0.0,
    "gyro_y": 0.0,
    "gyro_z": 0.0,
    "mag_x": 0.0,
    "mag_y": 0.0,
    "mag_z": 0.0,
  };

  late WebSocketChannel channel;
  Timer? _timer;
  String serverMessage = "Waiting for server..."; // Will hold server text

  @override
  void initState() {
    super.initState();

    // Connect to WebSocket server
    channel = WebSocketChannel.connect(
      Uri.parse('ws://1c1a681c7902.ngrok-free.app/ws/read/'), // Replace with your WebSocket URL
    );

    // Listen for messages from the server
    channel.stream.listen((message) {
      setState(() {
        serverMessage = message; // Update the container with received text
      });
    });

    // Listen to accelerometer
    accelerometerEvents.listen((event) {
      imuData["accel_x"] = event.x;
      imuData["accel_y"] = event.y;
      imuData["accel_z"] = event.z;
    });

    // Listen to gyroscope
    gyroscopeEvents.listen((event) {
      imuData["gyro_x"] = event.x;
      imuData["gyro_y"] = event.y;
      imuData["gyro_z"] = event.z;
    });

    // Listen to magnetometer
    magnetometerEvents.listen((event) {
      imuData["mag_x"] = event.x;
      imuData["mag_y"] = event.y;
      imuData["mag_z"] = event.z;
    });

    // Send IMU data every 0.1 second
    _timer = Timer.periodic(Duration(milliseconds: 100), (_) {
      sendIMUData();
    });
  }

  void sendIMUData() {
    channel.sink.add(jsonEncode(imuData));
  }

  @override
  void dispose() {
    _timer?.cancel();
    channel.sink.close();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    double width = MediaQuery.of(context).size.width;
    double height = MediaQuery.of(context).size.height;

    return Scaffold(
      appBar: AppBar(
        title: const Text("Raven", style: TextStyle(color: Colors.black)),
        centerTitle: true,
        backgroundColor: const Color(0xFF40AED3),
      ),
      body: Center(
        child: Column(
          children: [
           /* ElevatedButton(
              onPressed: () {
                Navigator.push(
                  context,
                  MaterialPageRoute(builder: (context) => MapSaver()),
                );
              },
              child: Text("map saver"),
            ),*/
            Container(
              height: height * 0.4,
              width: width,
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: Colors.black, width: 2),
              ),
              child: Padding(
                padding: const EdgeInsets.all(8.0),
                child: ListView(
                  children: imuData.entries.map((entry) {
                    return Text(
                      "${entry.key}: ${entry.value.toStringAsFixed(4)}",
                      style: const TextStyle(color: Colors.black, fontSize: 12),
                    );
                  }).toList(),
                ),
              ),
            ),
            // Container to display server text
            Container(
              height: height * 0.1,
              width: width,
              margin: const EdgeInsets.only(top: 10),
              decoration: BoxDecoration(
                color: Colors.yellow[200],
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: Colors.black, width: 2),
              ),
              child: Center(
                child: Text(
                  serverMessage, // Show the received message here
                  style: const TextStyle(color: Colors.black, fontSize: 14),
                ),
              ),
            ),
            /*Container(
              height: height * 0.4,
              width: width,
              decoration: BoxDecoration(
                color: const Color(0xFF40AED3),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: Colors.black, width: 2),
              ),
              child: const Center(
                child: Text(
                  "hold and speak",
                  style: TextStyle(color: Colors.black, fontSize: 10),
                ),
              ),
            ),*/
          ],
        ),
      ),
    );
  }
}
