import 'package:flutter/material.dart';
/*
*
* -------------------------to be continued (this file for future update)----------------------------
*
*
* */
class MapSaver extends StatefulWidget {
  const MapSaver({super.key});

  @override
  State<MapSaver> createState() => _MapSaverState();
}

class _MapSaverState extends State<MapSaver> {
  TextEditingController valueController = TextEditingController();
  @override
  Widget build(BuildContext context) {
    var height =MediaQuery.of(context).size.height;
    var width =MediaQuery.of(context).size.width;
    return Scaffold(
      appBar: AppBar(
        title: const Text("map saver", style: TextStyle(color: Colors.black)),
        centerTitle: true,
        backgroundColor: const Color(0xFF40AED3),
      ),
      body: Center(
        child: Column(
          children: [
            SizedBox(
              height: 100,
            ),
            SizedBox(
              width: width*0.5,
              child: TextField(
                controller: valueController,
                decoration: InputDecoration(
                    border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(25)),
                    hintText: "enter the name",
                    helperText: "enter the name ",
                    suffixIconColor: Colors.blue),
              ),
            ),
            SizedBox(
              height: 100,
            ),
            ElevatedButton(
              onPressed: () async {},
              child: Text("save location"),
            ),
            ElevatedButton(
              onPressed: () async {},
              child: Text("save must point"),
            ),

          ],
        ),
      ),
    );
  }
}
